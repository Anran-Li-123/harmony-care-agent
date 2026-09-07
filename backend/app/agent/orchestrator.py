from __future__ import annotations

from app.agent.knowledge import KnowledgeRetriever
from app.agent.llm import LLMProvider
from app.agent.memory import MemoryExtractor, ProfileUpdater
from app.agent.safety import SafetyPolicy
from app.devices.adapters import ActionRouter
from app.schemas.models import (
    AgentDecision,
    CareEvent,
    ContextState,
    DeviceAction,
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

    def run(self, state: ContextState, event: CareEvent) -> AgentDecision:
        timeline = [
            TimelineItem(title="新事件进入系统", detail=f"{event.source} · {event.type}", stage="event", tone="info"),
            TimelineItem(title="上下文已组装", detail="短期记忆、近期事件、画像、设备与环境状态已按需收集", stage="context", tone="info"),
        ]
        context = self.assembler.assemble(state, event)
        forced_risk, safety_evidence = self.safety.evaluate(context, event)
        retrieved = self.knowledge.retrieve(context, event)
        timeline.append(TimelineItem(title="知识检索完成", detail=f"命中 {len(retrieved)} 条家庭规则", stage="knowledge", tone="info"))
        if forced_risk:
            payload = {"risk_level": forced_risk.value, "summary": self._safety_summary(event), "evidence": safety_evidence}
            timeline.append(TimelineItem(title="安全策略已接管", detail="明确风险采用确定性处置，不依赖模型猜测", stage="safety", tone="danger"))
        else:
            try:
                payload = self.provider.decide(context, event, [item.content for item in retrieved])
            except Exception as exc:  # Real mode remains demonstrable on timeout/invalid JSON.
                payload = {"risk_level": "low", "summary": "模型暂不可用，系统已降级为安全陪伴与持续观察。", "evidence": [f"LLM 降级：{type(exc).__name__}"]}
            timeline.append(TimelineItem(title="AI 决策完成", detail="已输出可验证的结构化结论", stage="decision", tone="success"))

        risk = RiskLevel(payload["risk_level"])
        actions = self._actions_for(event, risk, context)
        decision = AgentDecision(
            risk_level=risk,
            summary=str(payload.get("summary", "已生成决策")),
            evidence=list(payload.get("evidence", [])),
            retrieved_knowledge=[item.title for item in retrieved],
            actions=actions,
            llm_mode=self.llm_mode, timeline=timeline,
        )
        decision.memory_updates = self.memory.extract(state, event, decision)
        episode_id = self.memory.apply(state, event, decision)
        decision.profile_candidates = self.profile.candidates(state, event, episode_id)
        decision.profile_changes = self.profile.apply(state, decision.profile_candidates, event.target_person_id)
        state.sync_legacy_projection(event.target_person_id)
        executions = self.router.dispatch(state, actions)
        for execution in executions:
            decision.timeline.append(TimelineItem(title="设备动作", detail=execution, stage="router", tone="danger" if risk == RiskLevel.HIGH else "success"))
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
    def _actions_for(event: CareEvent, risk: RiskLevel, context: ContextState) -> list[DeviceAction]:
        if event.source == "fall_detector":
            location = str(event.data.get("location", "bedroom"))
            return [
                DeviceAction(target="robot", action="move_to", parameters={"location": location}, priority=Priority.CRITICAL, rationale="现场确认"),
                DeviceAction(target="robot", action="speak", parameters={"text": "李爷爷，您还好吗？我正在确认您的情况。"}, priority=Priority.CRITICAL, rationale="语音安抚与确认"),
                DeviceAction(target="robot", action="camera_check", parameters={"location": location}, priority=Priority.HIGH, rationale="辅助确认现场"),
                DeviceAction(target="watch", action="vibrate", parameters={"message": "检测到异常，请确认您的状态"}, priority=Priority.CRITICAL, rationale="紧急触达"),
                DeviceAction(target="watch", action="health_check", parameters={}, priority=Priority.HIGH, rationale="请求状态确认"),
                DeviceAction(target="phone", action="push_notification", parameters={"message": "家庭看护提醒：卧室疑似跌倒，机器人正在现场确认。"}, priority=Priority.CRITICAL, rationale="通知家属"),
            ]
        if event.source == "door_sensor":
            return [
                DeviceAction(target="robot", action="move_to", parameters={"location": "entrance"}, priority=Priority.HIGH, rationale="在安全距离观察入口"),
                DeviceAction(target="robot", action="speak", parameters={"text": "小安，请不要开门。我正在查看门口情况。"}, priority=Priority.HIGH, rationale="儿童安全提醒"),
                DeviceAction(target="watch", action="vibrate", parameters={"message": "请不要独自开门，等待家长确认"}, priority=Priority.HIGH, rationale="私密提醒"),
                DeviceAction(target="phone", action="push_notification", parameters={"message": "儿童看护提醒：入口门磁已打开，机器人正在观察。"}, priority=Priority.HIGH, rationale="通知家长"),
            ]
        if event.source == "watch_activity":
            location = str(event.data.get("location", "bedroom"))
            return [
                DeviceAction(target="robot", action="move_to", parameters={"location": location}, priority=Priority.HIGH, rationale="前往现场进行非医疗状态确认"),
                DeviceAction(target="robot", action="speak", parameters={"text": "李爷爷，我注意到您有一段时间没有活动，需要我帮忙吗？"}, priority=Priority.HIGH, rationale="温和请求用户确认"),
                DeviceAction(target="watch", action="vibrate", parameters={"message": "请轻触屏幕确认状态"}, priority=Priority.HIGH, rationale="请求本人确认"),
                DeviceAction(target="phone", action="push_notification", parameters={"message": "家庭看护提醒：手表记录到长时静止，机器人正在请求确认。"}, priority=Priority.HIGH, rationale="同步监护人但不作医疗判断"),
            ]
        if event.source == "watch_geofence":
            return [
                DeviceAction(target="watch", action="vibrate", parameters={"message": "你已离开家庭安全区，请在安全位置等待家长联系"}, priority=Priority.CRITICAL, rationale="直接提醒儿童"),
                DeviceAction(target="phone", action="push_notification", parameters={"message": "儿童看护提醒：小安已离开家庭安全区，请确认当前位置。"}, priority=Priority.CRITICAL, rationale="立即通知监护人"),
                DeviceAction(target="robot", action="wait", parameters={}, priority=Priority.NORMAL, rationale="保留家庭端观察能力"),
            ]
        if event.type == "device" and event.data.get("online") is False:
            if event.source == "phone":
                return [
                    DeviceAction(target="watch", action="vibrate", parameters={"message": "监护人手机暂未连接，家庭端将继续观察"}, priority=Priority.HIGH, rationale="启用可用终端提醒"),
                    DeviceAction(target="robot", action="speak", parameters={"text": "监护人手机暂时离线，我会继续在家中陪伴并记录状态。"}, priority=Priority.HIGH, rationale="透明说明降级状态"),
                ]
            return [
                DeviceAction(target="robot", action="speak", parameters={"text": "手表连接暂时中断，请确认是否正常佩戴。"}, priority=Priority.HIGH, rationale="通过现场终端补充确认"),
                DeviceAction(target="phone", action="push_notification", parameters={"message": "设备提醒：家庭手表连接中断，机器人正在提示检查。"}, priority=Priority.HIGH, rationale="改由在线手机通知"),
            ]
        text = str(event.data.get("text", ""))
        if "无聊" in text:
            preferred = context.user_profile.get("preferred_entertainment")
            recommendation = preferred.value if preferred else "轻松聊天"
            return [
                DeviceAction(target="robot", action="speak", parameters={"text": f"李爷爷，要不要听一段您喜欢的{recommendation}？我也可以陪您聊聊。"}, priority=Priority.NORMAL, rationale="按长期偏好提供低打扰陪伴"),
                DeviceAction(target="robot", action="play_audio", parameters={"content": recommendation}, priority=Priority.NORMAL, rationale="提供可选择的内容"),
            ]
        if event.data.get("preferred_name") or "李爷爷" in text or "叫我" in text:
            preferred_name = str(event.data.get("preferred_name", "李爷爷"))
            return [DeviceAction(target="robot", action="speak", parameters={"text": f"好的，{preferred_name}。很高兴认识您，我会这样称呼您。"}, priority=Priority.NORMAL, rationale="确认明确偏好")]
        if event.data.get("kind") == "sleep_pattern_review":
            return [DeviceAction(target="robot", action="speak", parameters={"text": "我注意到您最近休息时间变晚了，会按新的作息提供更合适的陪伴。"}, priority=Priority.LOW, rationale="透明地告知画像变化")]
        return [DeviceAction(target="robot", action="wait", parameters={}, priority=Priority.LOW, rationale="继续观察")]
