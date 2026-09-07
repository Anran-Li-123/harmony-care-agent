from __future__ import annotations

from collections import Counter
from typing import Any

from app.devices.registry import DeviceRegistry
from app.schemas.models import (
    ActionIntent,
    AgentPlan,
    CareEvent,
    CareGoal,
    CareGoalStatus,
    ContextState,
    DeviceAction,
    DeviceExecutionResult,
    DeviceType,
    FeedbackEvent,
    GoalEvaluation,
    GoalEvaluationOutcome,
    PlanCapabilityRequest,
    PlanStep,
    PlanStepStatus,
    Priority,
    RiskLevel,
    WorldState,
)


class CarePlanner:
    """Builds goal/plan semantics without selecting concrete device IDs."""

    def plan(
        self,
        world: WorldState,
        risk: RiskLevel,
        event: CareEvent,
        context: ContextState,
        available_capabilities: set[str],
        llm_payload: dict[str, Any] | None = None,
    ) -> tuple[CareGoal, AgentPlan]:
        if event.source == "fall_detector" and risk == RiskLevel.HIGH:
            return self._fall(world, event)
        if event.source == "door_sensor" and event.target_person_id == "child_xiaoyu" and risk in {RiskLevel.MEDIUM, RiskLevel.HIGH}:
            return self._child_door(event)
        if event.source == "watch_geofence" and risk == RiskLevel.HIGH:
            return self._safe_zone(event)
        if event.source == "watch_activity" and risk == RiskLevel.MEDIUM:
            return self._watch_confirmation(event)
        if event.type == "device" and event.data.get("online") is False and risk == RiskLevel.MEDIUM:
            return self._device_fallback(event, context)
        return self._companionship(event, context, available_capabilities, llm_payload or {})

    def action_intents(self, plan: AgentPlan) -> list[ActionIntent]:
        intents: list[ActionIntent] = []
        stationary_types = {DeviceType.LIGHT, DeviceType.DOOR_LOCK, DeviceType.SMART_SCREEN}
        for step in plan.steps:
            for request in step.capability_requests:
                parameters = dict(request.parameters)
                if request.target_location and request.capability in {"navigate_to", "observe"}:
                    parameters.setdefault("location", request.target_location)
                intents.append(ActionIntent(
                    capability=request.capability,
                    parameters=parameters,
                    priority=step.priority,
                    reason=step.description,
                    device_type=request.device_type,
                    location=request.target_location if request.device_type in stationary_types else None,
                    target_person_id=request.target_person_id,
                ))
        return intents

    def plan_follow_up(self, goal: CareGoal, evaluation: GoalEvaluation, world: WorldState, context: ContextState, feedback: FeedbackEvent) -> AgentPlan:
        if goal.goal_type in {"confirm_person_safety", "confirm_person_status"}:
            return self._person_follow_up(goal, evaluation, feedback)
        if goal.goal_type == "keep_child_safe_from_unknown_visitor":
            return self._child_door_follow_up(goal, evaluation, feedback)
        raise ValueError(f"当前 Goal 类型暂不支持 Follow-up Plan：{goal.goal_type}")

    @staticmethod
    def update_after_execution(goal: CareGoal, plan: AgentPlan, actions: list[DeviceAction], results: list[DeviceExecutionResult], *, preserve_goal_status: bool = False) -> None:
        successful = Counter(result.capability for result in results if result.success)
        for step in plan.steps:
            if not step.capability_requests:
                if step.intent.startswith("await_"):
                    step.status = PlanStepStatus.AWAITING_FEEDBACK
                continue
            required = Counter(request.capability for request in step.capability_requests)
            if all(successful[capability] >= count for capability, count in required.items()):
                step.status = PlanStepStatus.COMPLETED
                successful.subtract(required)
            elif any(action.capability in required for action in actions):
                step.status = PlanStepStatus.ACTIVE
        executable_complete = all(step.status == PlanStepStatus.COMPLETED for step in plan.steps if step.capability_requests)
        if preserve_goal_status or goal.status == CareGoalStatus.COMPLETED:
            return
        has_feedback_wait = any(step.status == PlanStepStatus.AWAITING_FEEDBACK for step in plan.steps)
        if goal.requires_feedback and has_feedback_wait:
            goal.status = CareGoalStatus.AWAITING_FEEDBACK
        elif not goal.requires_feedback and executable_complete:
            goal.status = CareGoalStatus.COMPLETED
        else:
            goal.status = CareGoalStatus.ACTIVE

    def _person_follow_up(self, goal: CareGoal, evaluation: GoalEvaluation, feedback: FeedbackEvent) -> AgentPlan:
        person_id = goal.target_person_id or "elder_li"
        if evaluation.outcome == GoalEvaluationOutcome.SUCCESS:
            steps = [
                self._step("reassure_person", "回应老人并说明会继续在附近陪伴", Priority.NORMAL, None, "speak", [self._request("speak", DeviceType.ROBOT, parameters={"text": "好的，我会在附近陪您一会儿，有需要请告诉我。"})]),
                self._step("stay_nearby", "机器人留在附近保持低打扰陪伴", Priority.LOW, None, "wait", [self._request("wait", DeviceType.ROBOT)]),
            ]
            return AgentPlan(goal_id=goal.goal_id, summary="确认用户能够正常交流后提供附近陪伴", steps=steps)
        if evaluation.outcome == GoalEvaluationOutcome.CONTINUE:
            steps = [
                self._step("request_response_again", "检测到活动恢复，继续请求老人明确回应", Priority.HIGH, None, "speak", [
                    self._request("speak", DeviceType.ROBOT, parameters={"text": "检测到您有活动，请确认现在是否需要帮助。"}),
                    self._request("request_confirmation", DeviceType.WATCH, person_id=person_id, parameters={"message": "检测到活动恢复，请确认是否需要帮助"}),
                ]),
                self._step("await_person_feedback", "继续等待老人明确反馈", Priority.HIGH),
            ]
            return AgentPlan(goal_id=goal.goal_id, summary="活动信号降低风险，但仍需本人明确确认", steps=steps)
        no_response = feedback.feedback_type.value == "no_response"
        prompt = "李爷爷，我还没有收到您的回应，请告诉我是否需要帮助。" if no_response else "我会留在这里陪您，已经再次通知家属，请不要勉强移动。"
        status = "老人尚未回应，系统正在持续现场确认" if no_response else "用户明确需要帮助，系统已升级通知"
        steps = [
            self._step("remain_on_scene", "机器人留在现场持续观察", Priority.HIGH, None, "wait", [self._request("wait", DeviceType.ROBOT)]),
            self._step("continue_voice_support", "机器人再次呼叫并继续语音陪伴", Priority.HIGH, None, "speak", [self._request("speak", DeviceType.ROBOT, parameters={"text": prompt})]),
            self._step("escalate_guardian_notice", "向监护人发送高优先级状态更新", Priority.CRITICAL, None, "push_notification", [self._request("push_notification", DeviceType.PHONE, person_id="guardian", parameters={"message": f"家庭看护升级提醒：{status}。"})]),
            self._step("show_escalated_status", "智慧屏显示持续关注状态", Priority.HIGH, None, "display_status", [self._request("display_status", DeviceType.SMART_SCREEN, parameters={"status": status})]),
            self._step("maintain_watch_alert", "老人手表继续提醒", Priority.HIGH, None, "vibrate", [self._request("vibrate", DeviceType.WATCH, person_id=person_id, parameters={"message": "请确认当前状态，家属已收到更新"})]),
            self._step("await_person_feedback", "继续等待老人或监护人反馈", Priority.HIGH),
        ]
        return AgentPlan(goal_id=goal.goal_id, summary="升级通知并保持机器人现场陪伴，不作医疗诊断", steps=steps)

    def _child_door_follow_up(self, goal: CareGoal, evaluation: GoalEvaluation, feedback: FeedbackEvent) -> AgentPlan:
        if evaluation.outcome == GoalEvaluationOutcome.SUCCESS:
            rejected = feedback.data.get("decision") == "rejected"
            message = "爸爸妈妈已经拒绝访客，请不要靠近门口，我会陪着你。" if rejected else "爸爸妈妈已经确认，请继续等待大人处理门锁。"
            steps = [
                self._step("keep_entrance_locked", "门锁继续保持锁定，不自动开门", Priority.HIGH, "entrance", "lock", [self._request("lock", DeviceType.DOOR_LOCK, location="entrance")]),
                self._step("guide_child_after_confirmation", "机器人向儿童说明监护人决定并继续安抚", Priority.NORMAL, None, "speak", [self._request("speak", DeviceType.ROBOT, parameters={"text": message})]),
            ]
            if rejected:
                steps.append(self._step("publish_resolution_status", "手机显示访客已被拒绝", Priority.NORMAL, None, "show_status", [self._request("show_status", DeviceType.PHONE, person_id="guardian", parameters={"message": "门口事件已处理：访客已拒绝，门锁保持锁定"})]))
            return AgentPlan(goal_id=goal.goal_id, summary="保持门锁锁定并向儿童说明监护人决定", steps=steps)
        steps = [
            self._step("keep_entrance_locked", "监护人未回应期间门锁继续保持锁定", Priority.HIGH, "entrance", "lock", [self._request("lock", DeviceType.DOOR_LOCK, location="entrance")]),
            self._step("continue_child_support", "机器人继续陪同并提醒儿童远离门口", Priority.HIGH, None, "speak", [self._request("speak", DeviceType.ROBOT, parameters={"text": "爸爸妈妈还没有回复，请继续远离门口，我会陪着你。"})]),
            self._step("maintain_safety_message", "智慧屏继续显示安全提示", Priority.HIGH, None, "show_message", [self._request("show_message", DeviceType.SMART_SCREEN, parameters={"message": "请远离门口，继续等待监护人确认"})]),
            self._step("repeat_guardian_notice", "再次通知监护人", Priority.HIGH, None, "push_notification", [self._request("push_notification", DeviceType.PHONE, person_id="guardian", parameters={"message": "儿童门口事件仍在等待确认，门锁保持锁定。"})]),
            self._step("await_guardian_confirmation", "继续等待监护人确认", Priority.HIGH, None, None, []),
        ]
        return AgentPlan(goal_id=goal.goal_id, summary="保持入口防护与儿童陪伴，继续等待监护人", steps=steps)

    def _fall(self, world: WorldState, event: CareEvent) -> tuple[CareGoal, AgentPlan]:
        person_id = event.target_person_id or "elder_li"
        person = world.people.get(person_id)
        name = person.name if person else "老人"
        location = (person.location if person else None) or str(event.data.get("location", "bedroom"))
        goal = CareGoal(goal_type="confirm_person_safety", target_person_id=person_id, description=f"确认{name}当前安全状态并提供现场看护", priority=Priority.HIGH, status=CareGoalStatus.ACTIVE, requires_feedback=True)
        steps = [
            self._step("improve_visibility", "打开通往卧室和卧室内的照明", Priority.HIGH, location, "switch", [
                self._request("switch", DeviceType.LIGHT, location="entrance", parameters={"value": "on"}),
                self._request("switch", DeviceType.LIGHT, location=location, parameters={"value": "on"}),
            ]),
            self._step("reach_target", f"机器人前往{name}所在卧室", Priority.HIGH, location, "navigate_to", [self._request("navigate_to", DeviceType.ROBOT, location=location)]),
            self._step("observe_target", "机器人进行现场观察", Priority.HIGH, location, "observe", [self._request("observe", DeviceType.ROBOT, location=location)]),
            self._step("request_response", f"请求{name}回应并确认当前状态", Priority.HIGH, location, "speak", [
                self._request("speak", DeviceType.ROBOT, parameters={"text": f"{name}，您还好吗？我正在确认您的情况。"}),
                self._request("vibrate", DeviceType.WATCH, person_id=person_id, parameters={"message": "检测到异常，请确认您的状态"}),
            ]),
            self._step("notify_guardian", "向监护人同步当前异常情况", Priority.HIGH, None, "push_notification", [self._request("push_notification", DeviceType.PHONE, person_id="guardian", parameters={"message": "家庭看护提醒：卧室疑似跌倒，机器人正在现场确认。"})]),
            self._step("await_person_feedback", f"等待{name}反馈", Priority.HIGH, location),
        ]
        return goal, AgentPlan(goal_id=goal.goal_id, summary=f"照明现场、抵达并观察{name}，同步监护人后等待本人反馈", steps=steps)

    def _child_door(self, event: CareEvent) -> tuple[CareGoal, AgentPlan]:
        person_id = event.target_person_id or "child_xiaoyu"
        goal = CareGoal(goal_type="keep_child_safe_from_unknown_visitor", target_person_id=person_id, description="确保儿童远离陌生访客，并等待监护人确认", priority=Priority.HIGH, status=CareGoalStatus.ACTIVE, requires_feedback=True)
        steps = [
            self._step("secure_entrance", "保持入口门锁锁定", Priority.HIGH, "entrance", "lock", [self._request("lock", DeviceType.DOOR_LOCK, location="entrance")]),
            self._step("position_robot", "机器人前往玄关安全位置", Priority.HIGH, "entrance", "navigate_to", [self._request("navigate_to", DeviceType.ROBOT, location="entrance")]),
            self._step("guide_child", "提醒儿童不要开门并保持安全距离", Priority.HIGH, "entrance", "speak", [
                self._request("speak", DeviceType.ROBOT, parameters={"text": "小宇，先不要开门，我们等爸爸妈妈确认。"}),
                self._request("vibrate", DeviceType.WATCH, person_id=person_id, parameters={"message": "请不要独自开门，等待家长确认"}),
            ]),
            self._step("show_safety_message", "智慧屏显示安全提示", Priority.HIGH, None, "show_message", [self._request("show_message", DeviceType.SMART_SCREEN, parameters={"message": "请不要独自开门，等待家长确认"})]),
            self._step("notify_guardian", "通知监护人当前门口事件", Priority.HIGH, None, "push_notification", [self._request("push_notification", DeviceType.PHONE, person_id="guardian", parameters={"message": "儿童看护提醒：入口门口事件，机器人正在陪伴小宇。"})]),
            self._step("await_guardian_confirmation", "等待监护人确认", Priority.HIGH),
        ]
        return goal, AgentPlan(goal_id=goal.goal_id, summary="锁定入口、引导儿童远离门口并通知监护人", steps=steps)

    def _safe_zone(self, event: CareEvent) -> tuple[CareGoal, AgentPlan]:
        person_id = event.target_person_id or "child_xiaoyu"
        goal = CareGoal(goal_type="restore_child_safe_contact", target_person_id=person_id, description="提醒儿童停留在安全位置并请监护人确认", priority=Priority.HIGH, status=CareGoalStatus.ACTIVE, requires_feedback=True)
        steps = [
            self._step("alert_child", "通过儿童手表发送安全提醒", Priority.HIGH, None, "vibrate", [self._request("vibrate", DeviceType.WATCH, person_id=person_id, parameters={"message": "你已离开家庭安全区，请在安全位置等待家长联系"})]),
            self._step("notify_guardian", "通知监护人确认儿童当前位置", Priority.HIGH, None, "push_notification", [self._request("push_notification", DeviceType.PHONE, person_id="guardian", parameters={"message": "儿童看护提醒：小宇已离开家庭安全区，请确认当前位置。"})]),
            self._step("maintain_home_observation", "家庭机器人保持观察", Priority.NORMAL, None, "wait", [self._request("wait", DeviceType.ROBOT)]),
            self._step("await_guardian_confirmation", "等待监护人确认", Priority.HIGH),
        ]
        return goal, AgentPlan(goal_id=goal.goal_id, summary="提醒儿童并同步监护人，等待位置确认", steps=steps)

    def _watch_confirmation(self, event: CareEvent) -> tuple[CareGoal, AgentPlan]:
        person_id = event.target_person_id or "elder_li"
        location = str(event.data.get("location", "bedroom"))
        goal = CareGoal(goal_type="confirm_person_status", target_person_id=person_id, description="确认老人长时静止后的当前状态", priority=Priority.HIGH, status=CareGoalStatus.ACTIVE, requires_feedback=True)
        steps = [
            self._step("reach_target", "机器人前往现场进行非医疗状态确认", Priority.HIGH, location, "navigate_to", [self._request("navigate_to", DeviceType.ROBOT, location=location)]),
            self._step("request_response", "通过机器人和手表请求本人确认", Priority.HIGH, location, "request_confirmation", [
                self._request("speak", DeviceType.ROBOT, parameters={"text": "李爷爷，我注意到您有一段时间没有活动，需要我帮忙吗？"}),
                self._request("request_confirmation", DeviceType.WATCH, person_id=person_id, parameters={"message": "请轻触屏幕确认状态"}),
            ]),
            self._step("notify_guardian", "同步监护人但不作医疗判断", Priority.HIGH, None, "push_notification", [self._request("push_notification", DeviceType.PHONE, person_id="guardian", parameters={"message": "家庭看护提醒：手表记录到长时静止，机器人正在请求确认。"})]),
            self._step("await_person_feedback", "等待老人反馈", Priority.HIGH),
        ]
        return goal, AgentPlan(goal_id=goal.goal_id, summary="现场请求老人确认并同步监护人", steps=steps)

    def _device_fallback(self, event: CareEvent, context: ContextState) -> tuple[CareGoal, AgentPlan]:
        offline = DeviceRegistry(context.devices).for_event_source(event.source, event.target_person_id)
        phone_offline = event.source == "phone" or bool(offline and offline.device_type == DeviceType.PHONE)
        goal = CareGoal(goal_type="maintain_care_during_device_outage", target_person_id=event.target_person_id, description="在关键设备离线时维持可用的家庭看护通道", priority=Priority.HIGH, status=CareGoalStatus.ACTIVE, requires_feedback=True)
        if phone_offline:
            requests = [
                self._request("show_message", DeviceType.WATCH, person_id=event.target_person_id if event.target_person_id in context.people else "elder_li", parameters={"message": "监护人手机暂未连接，家庭端将继续观察"}),
                self._request("speak", DeviceType.ROBOT, parameters={"text": "监护人手机暂时离线，我会继续在家中陪伴并记录状态。"}),
                self._request("display_status", DeviceType.SMART_SCREEN, parameters={"status": "监护人手机离线，家庭端持续观察"}),
            ]
        else:
            requests = [
                self._request("speak", DeviceType.ROBOT, parameters={"text": "手表连接暂时中断，请确认是否正常佩戴。"}),
                self._request("push_notification", DeviceType.PHONE, person_id="guardian", parameters={"message": "设备提醒：家庭手表连接中断，机器人正在提示检查。"}),
                self._request("display_status", DeviceType.SMART_SCREEN, parameters={"status": "手表连接中断，请检查佩戴状态"}),
            ]
        steps = [self._step("activate_fallback_channels", "使用仍在线的家庭终端维持提醒", Priority.HIGH, None, requests[0].capability, requests), self._step("await_device_confirmation", "等待设备状态确认", Priority.HIGH)]
        return goal, AgentPlan(goal_id=goal.goal_id, summary="跳过离线设备并启用确定性降级通道", steps=steps)

    def _companionship(self, event: CareEvent, context: ContextState, available: set[str], llm_payload: dict[str, Any]) -> tuple[CareGoal, AgentPlan]:
        person_id = event.target_person_id or "elder_li"
        person = context.people.get(person_id)
        name = person.name if person else "家庭成员"
        text = str(event.data.get("text", ""))
        goal_type = "provide_companionship"
        description = f"为{name}提供低打扰陪伴"
        requests: list[PlanCapabilityRequest]
        intent = "provide_presence"
        step_description = "保持陪伴并继续观察"
        if "无聊" in text:
            preferred = context.user_profile.get("preferred_entertainment")
            content = str(preferred.value) if preferred else "轻松聊天"
            requests = [self._request("speak", DeviceType.ROBOT, parameters={"text": f"{name}，要不要听一段您喜欢的{content}？我也可以陪您聊聊。"})]
            if "play_audio" in available:
                requests.append(self._request("play_audio", DeviceType.ROBOT, parameters={"content": content}))
            intent, step_description = "engage_person", "按偏好提供对话或陪伴内容"
        elif event.data.get("preferred_name") or "叫我" in text:
            preferred_name = str(event.data.get("preferred_name", "李爷爷"))
            goal_type, description = "respect_person_preference", f"确认并尊重{preferred_name}的称呼偏好"
            intent, step_description = "confirm_preference", "通过语音确认明确称呼偏好"
            requests = [self._request("speak", DeviceType.ROBOT, parameters={"text": f"好的，{preferred_name}。很高兴认识您，我会这样称呼您。"})]
        elif event.data.get("kind") == "sleep_pattern_review":
            goal_type, description = "adapt_companionship_routine", f"根据{name}的近期作息调整陪伴方式"
            intent, step_description = "acknowledge_routine_change", "透明说明作息画像变化"
            requests = [self._request("speak", DeviceType.ROBOT, parameters={"text": "我注意到您最近休息时间变晚了，会按新的作息提供更合适的陪伴。"})]
        else:
            requests = [self._request("wait", DeviceType.ROBOT)]
        goal = CareGoal(goal_type=goal_type, target_person_id=person_id, description=description, priority=Priority.LOW, status=CareGoalStatus.ACTIVE, requires_feedback=False)
        step = self._step(intent, step_description, Priority.LOW, None, requests[0].capability, requests)
        summary = str(llm_payload.get("summary") or description)
        return goal, AgentPlan(goal_id=goal.goal_id, summary=summary, steps=[step])

    @staticmethod
    def _request(capability: str, device_type: DeviceType, *, location: str | None = None, person_id: str | None = None, parameters: dict[str, Any] | None = None) -> PlanCapabilityRequest:
        return PlanCapabilityRequest(capability=capability, device_type=device_type, target_location=location, target_person_id=person_id, parameters=parameters or {})

    @staticmethod
    def _step(intent: str, description: str, priority: Priority, location: str | None = None, capability: str | None = None, requests: list[PlanCapabilityRequest] | None = None) -> PlanStep:
        return PlanStep(intent=intent, description=description, priority=priority, target_location=location, required_capability=capability, capability_requests=requests or [])
