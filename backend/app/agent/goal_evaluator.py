from __future__ import annotations

from app.schemas.models import (
    AgentPlan,
    CareGoal,
    CareGoalStatus,
    ContextState,
    FeedbackEvent,
    FeedbackType,
    GoalEvaluation,
    GoalEvaluationOutcome,
    RiskLevel,
    WorldState,
)


class GoalEvaluator:
    """Deterministic safety evaluation for feedback on an existing goal."""

    def evaluate(
        self,
        goal: CareGoal,
        plan: AgentPlan,
        feedback: FeedbackEvent,
        context: ContextState,
        world: WorldState,
        previous_risk: RiskLevel,
    ) -> GoalEvaluation:
        if goal.goal_type in {"confirm_person_safety", "confirm_person_status"}:
            return self._person_safety(goal, feedback, previous_risk)
        if goal.goal_type == "keep_child_safe_from_unknown_visitor":
            return self._child_door(goal, feedback, previous_risk)
        raise ValueError(f"当前 Goal 类型暂不支持反馈闭环：{goal.goal_type}")

    @staticmethod
    def _person_safety(goal: CareGoal, feedback: FeedbackEvent, previous_risk: RiskLevel) -> GoalEvaluation:
        if feedback.feedback_type == FeedbackType.USER_RESPONSE:
            response = feedback.data["response"]
            if response == "im_fine":
                return GoalEvaluation(goal_id=goal.goal_id, outcome=GoalEvaluationOutcome.SUCCESS, summary="用户已明确回应且能够正常交流，现场确认完成。", evidence=["用户通过机器人麦克风明确回应", "当前语义状态已标记为 responsive confirmed", "未作医学诊断"], previous_risk_level=previous_risk, updated_risk_level=RiskLevel.MEDIUM, goal_status=CareGoalStatus.COMPLETED, requires_follow_up=True)
            return GoalEvaluation(goal_id=goal.goal_id, outcome=GoalEvaluationOutcome.ESCALATE, summary="用户明确表示需要帮助，系统升级通知并继续现场陪伴。", evidence=["用户明确反馈需要帮助" if response == "need_help" else "用户明确反馈无法自行站起", "安全目标不能标记完成", "不推断疾病或损伤类型"], previous_risk_level=previous_risk, updated_risk_level=RiskLevel.HIGH, goal_status=CareGoalStatus.AWAITING_FEEDBACK, requires_follow_up=True)
        if feedback.feedback_type == FeedbackType.NO_RESPONSE:
            return GoalEvaluation(goal_id=goal.goal_id, outcome=GoalEvaluationOutcome.ESCALATE, summary="等待时间内未收到回应，需要再次呼叫并升级监护人通知。", evidence=["当前没有收到用户回应", "不能据此推断更严重状态", "需要继续现场观察"], previous_risk_level=previous_risk, updated_risk_level=RiskLevel.HIGH, goal_status=CareGoalStatus.AWAITING_FEEDBACK, requires_follow_up=True)
        if feedback.feedback_type == FeedbackType.WATCH_ACTIVITY:
            return GoalEvaluation(goal_id=goal.goal_id, outcome=GoalEvaluationOutcome.CONTINUE, summary="手表检测到活动恢复，但单一传感器信号不足以结束安全目标。", evidence=["手表重新检测到活动", "仍缺少用户明确回应", "继续请求本人确认"], previous_risk_level=previous_risk, updated_risk_level=RiskLevel.MEDIUM, goal_status=CareGoalStatus.AWAITING_FEEDBACK, requires_follow_up=True)
        raise ValueError("老人安全 Goal 仅接受 user_response、no_response 或 watch_activity")

    @staticmethod
    def _child_door(goal: CareGoal, feedback: FeedbackEvent, previous_risk: RiskLevel) -> GoalEvaluation:
        if feedback.feedback_type == FeedbackType.GUARDIAN_CONFIRMATION:
            decision = feedback.data["decision"]
            summary = "监护人已确认访客，儿童继续等待大人处理门锁。" if decision == "confirmed" else "监护人已拒绝访客，儿童门口安全流程完成。"
            evidence = ["监护人已明确确认访客" if decision == "confirmed" else "监护人已明确拒绝访客", "门锁继续保持锁定", "Care Agent 未执行自动解锁"]
            return GoalEvaluation(goal_id=goal.goal_id, outcome=GoalEvaluationOutcome.SUCCESS, summary=summary, evidence=evidence, previous_risk_level=previous_risk, updated_risk_level=RiskLevel.LOW, goal_status=CareGoalStatus.COMPLETED, requires_follow_up=True)
        if feedback.feedback_type == FeedbackType.GUARDIAN_NO_RESPONSE:
            return GoalEvaluation(goal_id=goal.goal_id, outcome=GoalEvaluationOutcome.CONTINUE, summary="监护人暂未回应，继续保持入口防护与儿童陪伴。", evidence=["监护人尚未确认", "门锁必须保持锁定", "继续使用家庭终端提醒"], previous_risk_level=previous_risk, updated_risk_level=RiskLevel.HIGH, goal_status=CareGoalStatus.AWAITING_FEEDBACK, requires_follow_up=True)
        raise ValueError("儿童门口 Goal 仅接受 guardian_confirmation 或 guardian_no_response")
