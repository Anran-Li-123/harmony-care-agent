from __future__ import annotations

from app.agent.knowledge import KnowledgeRetriever
from app.agent.llm import LLMProvider
from app.agent.memory import MemoryExtractor, ProfileUpdater
from app.agent.safety import SafetyPolicy
from app.agent.world_model import WorldModelBuilder
from app.devices.adapters import ActionRouter
from app.devices.registry import DeviceRegistry
from app.schemas.models import (
    AgentDecision,
    ActionIntent,
    CareEvent,
    ContextState,
    DeviceType,
    Priority,
    RiskLevel,
    TimelineItem,
)


class ContextAssembler:
    """Provides a bounded view; full historical memory is never blindly sent to an LLM."""

    def assemble(self, state: ContextState, event: CareEvent) -> ContextState:
        clone = state.model_copy(deep=True)
        target = clone.target_person(event.target_person_id)
        for person in clone.people.values():
            if target and person.person_id == target.person_id:
                person.working_memory = person.working_memory[-6:]
                person.episodic_memory = person.episodic_memory[-6:]
            else:
                # Keep household identity/location/status, not another person's long history.
                person.working_memory = []
                person.episodic_memory = []
                person.user_profile = {}
        clone.sync_legacy_projection(event.target_person_id)
        return clone


class AgentOrchestrator:
    def __init__(self, provider: LLMProvider, llm_mode: str) -> None:
        self.provider = provider
        self.llm_mode = llm_mode
        self.safety = SafetyPolicy()
        self.knowledge = KnowledgeRetriever()
        self.assembler = ContextAssembler()
        self.memory = MemoryExtractor()
        self.profile = ProfileUpdater()
        self.router = ActionRouter()
        self.world_model = WorldModelBuilder()

    def run(self, state: ContextState, event: CareEvent) -> AgentDecision:
        world_state = self.world_model.build(state, event)
        timeline = [
            TimelineItem(title="新事件进入系统", detail=f"{event.source} · {event.type}", stage="event", tone="info"),
            TimelineItem(title="当前世界状态已构建", detail=f"识别 {len(world_state.people)} 位家庭成员、{len(world_state.rooms)} 个语义空间", stage="world-model", tone="info"),
            TimelineItem(title="上下文已组装", detail="短期记忆、近期事件、画像、设备与环境状态已按需收集", stage="context", tone="info"),
        ]
        context = self.assembler.assemble(state, event)
        forced_risk, safety_evidence = self.safety.evaluate(context, event, world_state)
        retrieved = self.knowledge.retrieve(context, event)
        timeline.append(TimelineItem(title="知识检索完成", detail=f"命中 {len(retrieved)} 条家庭规则", stage="knowledge", tone="info"))
        if forced_risk:
            payload = {"risk_level": forced_risk.value, "summary": self._safety_summary(event), "evidence": safety_evidence}
            timeline.append(TimelineItem(title="安全策略已接管", detail="明确风险采用确定性处置，不依赖模型猜测", stage="safety", tone="danger"))
        else:
            try:
                payload = self.provider.decide(context, event, [item.content for item in retrieved], world_state)
            except Exception as exc:  # Real mode remains demonstrable on timeout/invalid JSON.
                payload = {"risk_level": "low", "summary": "模型暂不可用，系统已降级为安全陪伴与持续观察。", "evidence": [f"LLM 降级：{type(exc).__name__}"]}
            timeline.append(TimelineItem(title="AI 决策完成", detail="已输出可验证的结构化结论", stage="decision", tone="success"))

        risk = RiskLevel(payload["risk_level"])
        intents = self._intents_for(event, risk, context)
        actions = self.router.resolve(state, intents)
        decision = AgentDecision(
            risk_level=risk,
            summary=str(payload.get("summary", "已生成决策")),
            evidence=list(payload.get("evidence", [])),
            retrieved_knowledge=[item.title for item in retrieved],
            actions=actions,
            world_state=world_state,
            llm_mode=self.llm_mode, timeline=timeline,
        )
        decision.memory_updates = self.memory.extract(state, event, decision)
        episode_id = self.memory.apply(state, event, decision)
        decision.profile_candidates = self.profile.candidates(state, event, episode_id)
        decision.profile_changes = self.profile.apply(state, decision.profile_candidates, event.target_person_id)
        state.sync_legacy_projection(event.target_person_id)
        executions = self.router.dispatch(state, actions)
        decision.execution_results = executions
        for execution in executions:
            decision.timeline.append(TimelineItem(title="设备动作", detail=execution.message, stage="router", tone="danger" if risk == RiskLevel.HIGH else "success"))
        decision.timeline.append(TimelineItem(title="记忆已更新", detail="工作记忆与事件记忆已写入；画像仅在规则允许且证据充足时更新", stage="memory", tone="success"))
        return decision

    @staticmethod
    def _safety_summary(event: CareEvent) -> str:
        if event.source == "fall_detector":
            return "检测到卧室疑似跌倒，需要立即确认老人状态。"
        if event.source == "door_sensor":
            return "检测到门口异常开启，需提醒儿童不要开门并通知家长。"
        if event.source == "watch_activity":
            return "手表记录到较长时间静止且用户未确认，需要通过家庭终端请求状态确认。"
        if event.source == "watch_geofence":
            return "儿童手表已离开家庭安全区，需要提醒儿童并通知监护人确认。"
        return "关键设备离线，已启用降级看护策略。"

    @staticmethod
    def _intents_for(event: CareEvent, risk: RiskLevel, context: ContextState) -> list[ActionIntent]:
        if event.source == "fall_detector":
            location = str(event.data.get("location", "bedroom"))
            return [
                ActionIntent(capability="switch", location="entrance", device_type=DeviceType.LIGHT, parameters={"value": "on"}, priority=Priority.CRITICAL, reason="照亮机器人前往卧室的通道"),
                ActionIntent(capability="switch", location=location, device_type=DeviceType.LIGHT, parameters={"value": "on"}, priority=Priority.CRITICAL, reason="照亮老人所在卧室"),
                ActionIntent(capability="navigate_to", device_type=DeviceType.ROBOT, parameters={"location": location}, priority=Priority.CRITICAL, reason="前往现场确认"),
                ActionIntent(capability="observe", device_type=DeviceType.ROBOT, parameters={"location": location}, priority=Priority.HIGH, reason="辅助确认现场"),
                ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": "李爷爷，您还好吗？我正在确认您的情况。"}, priority=Priority.CRITICAL, reason="语音安抚与确认"),
                ActionIntent(capability="vibrate", device_type=DeviceType.WATCH, target_person_id="elder_li", parameters={"message": "检测到异常，请确认您的状态"}, priority=Priority.CRITICAL, reason="紧急触达老人"),
                ActionIntent(capability="push_notification", device_type=DeviceType.PHONE, target_person_id="guardian", parameters={"message": "家庭看护提醒：卧室疑似跌倒，机器人正在现场确认。"}, priority=Priority.CRITICAL, reason="通知监护人"),
            ]
        if event.source == "door_sensor":
            return [
                ActionIntent(capability="lock", location="entrance", device_type=DeviceType.DOOR_LOCK, priority=Priority.CRITICAL, reason="保持入口门锁锁定"),
                ActionIntent(capability="navigate_to", device_type=DeviceType.ROBOT, parameters={"location": "entrance"}, priority=Priority.HIGH, reason="在安全距离观察入口"),
                ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": "小宇，先不要开门，我们等爸爸妈妈确认。"}, priority=Priority.HIGH, reason="儿童安全提醒"),
                ActionIntent(capability="show_message", device_type=DeviceType.SMART_SCREEN, parameters={"message": "请不要独自开门，等待家长确认"}, priority=Priority.HIGH, reason="在家庭智慧屏显示安全提示"),
                ActionIntent(capability="vibrate", device_type=DeviceType.WATCH, target_person_id="child_xiaoyu", parameters={"message": "请不要独自开门，等待家长确认"}, priority=Priority.HIGH, reason="提醒儿童"),
                ActionIntent(capability="push_notification", device_type=DeviceType.PHONE, target_person_id="guardian", parameters={"message": "儿童看护提醒：入口门口事件，机器人正在陪伴小宇。"}, priority=Priority.HIGH, reason="通知监护人"),
            ]
        if event.source == "watch_activity":
            location = str(event.data.get("location", "bedroom"))
            return [
                ActionIntent(capability="navigate_to", device_type=DeviceType.ROBOT, parameters={"location": location}, priority=Priority.HIGH, reason="前往现场进行非医疗状态确认"),
                ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": "李爷爷，我注意到您有一段时间没有活动，需要我帮忙吗？"}, priority=Priority.HIGH, reason="温和请求用户确认"),
                ActionIntent(capability="request_confirmation", device_type=DeviceType.WATCH, target_person_id="elder_li", parameters={"message": "请轻触屏幕确认状态"}, priority=Priority.HIGH, reason="请求本人确认"),
                ActionIntent(capability="push_notification", device_type=DeviceType.PHONE, target_person_id="guardian", parameters={"message": "家庭看护提醒：手表记录到长时静止，机器人正在请求确认。"}, priority=Priority.HIGH, reason="同步监护人但不作医疗判断"),
            ]
        if event.source == "watch_geofence":
            return [
                ActionIntent(capability="vibrate", device_type=DeviceType.WATCH, target_person_id="child_xiaoyu", parameters={"message": "你已离开家庭安全区，请在安全位置等待家长联系"}, priority=Priority.CRITICAL, reason="直接提醒儿童"),
                ActionIntent(capability="push_notification", device_type=DeviceType.PHONE, target_person_id="guardian", parameters={"message": "儿童看护提醒：小宇已离开家庭安全区，请确认当前位置。"}, priority=Priority.CRITICAL, reason="立即通知监护人"),
                ActionIntent(capability="wait", device_type=DeviceType.ROBOT, priority=Priority.NORMAL, reason="保留家庭端观察能力"),
            ]
        if event.type == "device" and event.data.get("online") is False:
            offline_device = DeviceRegistry(context.devices).for_event_source(event.source, event.target_person_id)
            if event.source == "phone" or (offline_device and offline_device.device_type == DeviceType.PHONE):
                return [
                    ActionIntent(capability="show_message", device_type=DeviceType.WATCH, target_person_id=event.target_person_id if event.target_person_id in context.people else "elder_li", parameters={"message": "监护人手机暂未连接，家庭端将继续观察"}, priority=Priority.HIGH, reason="启用可用个人终端提醒"),
                    ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": "监护人手机暂时离线，我会继续在家中陪伴并记录状态。"}, priority=Priority.HIGH, reason="透明说明降级状态"),
                    ActionIntent(capability="display_status", device_type=DeviceType.SMART_SCREEN, parameters={"status": "监护人手机离线，家庭端持续观察"}, priority=Priority.NORMAL, reason="使用在线家庭终端显示状态"),
                ]
            return [
                ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": "手表连接暂时中断，请确认是否正常佩戴。"}, priority=Priority.HIGH, reason="通过现场终端补充确认"),
                ActionIntent(capability="push_notification", device_type=DeviceType.PHONE, target_person_id="guardian", parameters={"message": "设备提醒：家庭手表连接中断，机器人正在提示检查。"}, priority=Priority.HIGH, reason="改由在线手机通知"),
                ActionIntent(capability="display_status", device_type=DeviceType.SMART_SCREEN, parameters={"status": "手表连接中断，请检查佩戴状态"}, priority=Priority.NORMAL, reason="家庭智慧屏补充提示"),
            ]
        text = str(event.data.get("text", ""))
        if "无聊" in text:
            preferred = context.user_profile.get("preferred_entertainment")
            recommendation = preferred.value if preferred else "轻松聊天"
            return [
                ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": f"李爷爷，要不要听一段您喜欢的{recommendation}？我也可以陪您聊聊。"}, priority=Priority.NORMAL, reason="按长期偏好提供低打扰陪伴"),
                ActionIntent(capability="play_audio", device_type=DeviceType.ROBOT, parameters={"content": recommendation}, priority=Priority.NORMAL, reason="提供可选择的内容"),
            ]
        if event.data.get("preferred_name") or "李爷爷" in text or "叫我" in text:
            preferred_name = str(event.data.get("preferred_name", "李爷爷"))
            return [ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": f"好的，{preferred_name}。很高兴认识您，我会这样称呼您。"}, priority=Priority.NORMAL, reason="确认明确偏好")]
        if event.data.get("kind") == "sleep_pattern_review":
            return [ActionIntent(capability="speak", device_type=DeviceType.ROBOT, parameters={"text": "我注意到您最近休息时间变晚了，会按新的作息提供更合适的陪伴。"}, priority=Priority.LOW, reason="透明地告知画像变化")]
        return [ActionIntent(capability="wait", device_type=DeviceType.ROBOT, priority=Priority.LOW, reason="继续观察")]
