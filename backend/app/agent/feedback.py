from __future__ import annotations

from app.agent.goal_evaluator import GoalEvaluator
from app.agent.memory import MemoryExtractor
from app.agent.planner import CarePlanner
from app.agent.world_model import WorldModelBuilder
from app.devices.adapters import ActionRouter
from app.schemas.models import (
    AgentPlan,
    CareEvent,
    CareGoal,
    ContextState,
    FeedbackEvent,
    FeedbackResponse,
    FeedbackType,
    RiskLevel,
    TimelineItem,
    WorkingMemoryItem,
)


class FeedbackProcessor:
    """Applies feedback as current-state evidence without touching long-term profiles."""

    def apply(self, context: ContextState, goal: CareGoal, feedback: FeedbackEvent) -> ContextState:
        person = context.target_person(goal.target_person_id)
        if person:
            person.working_memory.append(WorkingMemoryItem(kind="feedback", content=self.summary(feedback)))
            person.working_memory = person.working_memory[-6:]
            if feedback.feedback_type == FeedbackType.USER_RESPONSE:
                response = feedback.data["response"]
                person.responsive = "confirmed"
                person.status = "responsive" if response == "im_fine" else "needs_help"
            elif feedback.feedback_type == FeedbackType.NO_RESPONSE:
                person.responsive = "unknown"
                person.status = "needs_confirmation"
            elif feedback.feedback_type == FeedbackType.WATCH_ACTIVITY:
                person.responsive = "unknown"
                person.status = "activity_detected_needs_confirmation"
                if "watch_activity" in context.sensors:
                    context.sensors["watch_activity"].status = "normal"
                    context.sensors["watch_activity"].value = feedback.data
            elif feedback.feedback_type == FeedbackType.GUARDIAN_CONFIRMATION:
                person.status = "safe_waiting_for_guardian"
            elif feedback.feedback_type == FeedbackType.GUARDIAN_NO_RESPONSE:
                person.status = "safety_concern"
            context.sync_legacy_projection(person.person_id)
        return context

    @staticmethod
    def summary(feedback: FeedbackEvent) -> str:
        if feedback.feedback_type == FeedbackType.USER_RESPONSE:
            labels = {"im_fine": "用户回应目前可以正常交流", "need_help": "用户明确表示需要帮助", "cannot_stand": "用户明确表示无法自行站起"}
            return labels[str(feedback.data["response"])]
        if feedback.feedback_type == FeedbackType.NO_RESPONSE:
            return "在等待时间内未收到用户回应"
        if feedback.feedback_type == FeedbackType.WATCH_ACTIVITY:
            return "手表重新检测到活动，但仍需本人确认"
        if feedback.feedback_type == FeedbackType.GUARDIAN_CONFIRMATION:
            return "监护人已确认访客" if feedback.data["decision"] == "confirmed" else "监护人已拒绝访客"
        return "监护人暂未回应"


class FeedbackCoordinator:
    """Runs one bounded observe-evaluate-follow-up cycle for the current goal."""

    def __init__(self) -> None:
        self.processor = FeedbackProcessor()
        self.evaluator = GoalEvaluator()
        self.planner = CarePlanner()
        self.router = ActionRouter()
        self.world_model = WorldModelBuilder()
        self.memory = MemoryExtractor()

    def run(self, context: ContextState, goal: CareGoal, plan: AgentPlan, originating_event: CareEvent, feedback: FeedbackEvent, previous_risk: RiskLevel) -> FeedbackResponse:
        timeline = [TimelineItem(title="反馈进入系统", detail=f"{feedback.feedback_type.value} · {feedback.source}", stage="feedback", tone="info")]
        self.processor.apply(context, goal, feedback)
        world = self.world_model.build(context)
        timeline.append(TimelineItem(title="当前世界状态已更新", detail="反馈已作为当前事实写入 Context，并重新构建 WorldState", stage="world-model", tone="info"))
        evaluation = self.evaluator.evaluate(goal, plan, feedback, context, world, previous_risk)
        goal.status = evaluation.goal_status
        timeline.append(TimelineItem(title="看护目标已评估", detail=f"{evaluation.outcome.value} · {previous_risk.value} → {evaluation.updated_risk_level.value}", stage="evaluation", tone="danger" if evaluation.outcome.value == "ESCALATE" else "success"))
        follow_up_plan = self.planner.plan_follow_up(goal, evaluation, world, context, feedback)
        timeline.append(TimelineItem(title="后续计划已生成", detail=follow_up_plan.summary, stage="planning", tone="info"))
        actions = self.router.resolve(context, self.planner.action_intents(follow_up_plan))
        timeline.append(TimelineItem(title="后续能力匹配完成", detail=f"{len(actions)} 个设备动作已绑定在线设备", stage="capability", tone="info"))
        results = self.router.dispatch(context, actions)
        self.planner.update_after_execution(goal, follow_up_plan, actions, results, preserve_goal_status=True)
        timeline.append(TimelineItem(title="后续设备动作已执行", detail=f"成功 {sum(result.success for result in results)} / {len(results)}", stage="execution", tone="success" if all(result.success for result in results) else "warning"))
        episode = self.memory.finalize_feedback(context, originating_event, feedback, evaluation, goal, [action.capability or action.action or "unknown" for action in actions])
        timeline.append(TimelineItem(title="目标状态已更新", detail=goal.status.value, stage="goal", tone="success" if goal.status.value == "completed" else "warning"))
        timeline.append(TimelineItem(title="事件记忆已收束", detail=episode.result if episode else "家庭运行状态已更新", stage="memory", tone="success" if episode and episode.status == "resolved" else "warning"))
        return FeedbackResponse(feedback=feedback, updated_world_state=world, goal_evaluation=evaluation, updated_goal=goal, follow_up_plan=follow_up_plan, actions=actions, execution_results=results, updated_context=context, timeline=timeline)
