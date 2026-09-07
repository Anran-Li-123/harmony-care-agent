from __future__ import annotations

from app.agent.knowledge import KnowledgeRetriever
from app.agent.llm import LLMProvider
from app.agent.memory import MemoryExtractor, ProfileUpdater
from app.agent.planner import CarePlanner
from app.agent.safety import SafetyPolicy
from app.agent.world_model import WorldModelBuilder
from app.devices.adapters import ActionRouter
from app.devices.registry import DeviceRegistry
from app.schemas.models import (
    AgentDecision,
    CareEvent,
    ContextState,
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
        self.planner = CarePlanner()
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
        registry = DeviceRegistry(state.devices)
        available_capabilities = {capability for device in registry.all() if device.online for capability in device.capabilities}
        care_goal, agent_plan = self.planner.plan(world_state, risk, event, context, available_capabilities, payload)
        timeline.append(TimelineItem(title="看护目标与计划已生成", detail=f"{care_goal.goal_type} · {len(agent_plan.steps)} 个高层步骤", stage="planning", tone="danger" if risk == RiskLevel.HIGH else "success"))
        actions = self.router.resolve(state, self.planner.action_intents(agent_plan))
        decision = AgentDecision(
            risk_level=risk,
            summary=str(payload.get("summary", "已生成决策")),
            evidence=list(payload.get("evidence", [])),
            retrieved_knowledge=[item.title for item in retrieved],
            actions=actions,
            care_goal=care_goal,
            agent_plan=agent_plan,
            world_state=world_state,
            llm_mode=self.llm_mode, timeline=timeline,
        )
        executions = self.router.dispatch(state, actions)
        decision.execution_results = executions
        self.planner.update_after_execution(care_goal, agent_plan, actions, executions)
        for execution in executions:
            decision.timeline.append(TimelineItem(title="设备动作", detail=execution.message, stage="router", tone="danger" if risk == RiskLevel.HIGH else "success"))
        decision.memory_updates = self.memory.extract(state, event, decision)
        episode_id = self.memory.apply(state, event, decision)
        decision.profile_candidates = self.profile.candidates(state, event, episode_id)
        decision.profile_changes = self.profile.apply(state, decision.profile_candidates, event.target_person_id)
        state.sync_legacy_projection(event.target_person_id)
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
