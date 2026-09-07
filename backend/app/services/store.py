from __future__ import annotations

from copy import deepcopy

from app.data.presets import preset_context
from app.schemas.models import AgentDecision, AgentPlan, CareEvent, CareGoal, CareGoalStatus, ContextState, FeedbackEvent, GoalEvaluation, RiskLevel


class DemoStore:
    """In-memory store behind interfaces that can later target Redis/PostgreSQL."""

    def __init__(self) -> None:
        self._context = preset_context("new-user")
        self._decisions: dict[str, AgentDecision] = {}
        self._active_goal: CareGoal | None = None
        self._active_plan: AgentPlan | None = None
        self._originating_event: CareEvent | None = None
        self._latest_feedback: FeedbackEvent | None = None
        self._latest_goal_evaluation: GoalEvaluation | None = None
        self._active_risk_level: RiskLevel | None = None

    def context(self) -> ContextState:
        return deepcopy(self._context)

    def replace_context(self, context: ContextState, *, clear_runtime: bool = True) -> ContextState:
        self._context = deepcopy(context)
        if clear_runtime:
            self._clear_goal_runtime(clear_evaluation=True)
        return self.context()

    def reset(self, preset_id: str = "new-user") -> ContextState:
        self._context = preset_context(preset_id)
        self._decisions = {}
        self._clear_goal_runtime(clear_evaluation=True)
        return self.context()

    def remember_decision(self, decision: AgentDecision, originating_event: CareEvent | None = None) -> None:
        self._decisions[decision.decision_id] = deepcopy(decision)
        if decision.care_goal and decision.care_goal.status in {CareGoalStatus.ACTIVE, CareGoalStatus.AWAITING_FEEDBACK}:
            self._active_goal = deepcopy(decision.care_goal)
            self._active_plan = deepcopy(decision.agent_plan)
            self._originating_event = deepcopy(originating_event)
            self._active_risk_level = decision.risk_level
            self._latest_feedback = None
            self._latest_goal_evaluation = None
        else:
            self._clear_goal_runtime(clear_evaluation=True)

    def decision(self, decision_id: str) -> AgentDecision | None:
        value = self._decisions.get(decision_id)
        return deepcopy(value) if value else None

    def active_goal(self) -> CareGoal | None:
        return deepcopy(self._active_goal)

    def active_plan(self) -> AgentPlan | None:
        return deepcopy(self._active_plan)

    def originating_event(self) -> CareEvent | None:
        return deepcopy(self._originating_event)

    def latest_feedback(self) -> FeedbackEvent | None:
        return deepcopy(self._latest_feedback)

    def latest_goal_evaluation(self) -> GoalEvaluation | None:
        return deepcopy(self._latest_goal_evaluation)

    def active_risk_level(self) -> RiskLevel | None:
        return self._active_risk_level

    def record_feedback(self, feedback: FeedbackEvent, evaluation: GoalEvaluation, goal: CareGoal, plan: AgentPlan) -> None:
        self._latest_goal_evaluation = deepcopy(evaluation)
        if goal.status == CareGoalStatus.COMPLETED:
            self._active_goal = None
            self._active_plan = None
            self._originating_event = None
            self._latest_feedback = None
            self._active_risk_level = None
            return
        self._active_goal = deepcopy(goal)
        self._active_plan = deepcopy(plan)
        self._latest_feedback = deepcopy(feedback)
        self._active_risk_level = evaluation.updated_risk_level

    def _clear_goal_runtime(self, *, clear_evaluation: bool) -> None:
        self._active_goal = None
        self._active_plan = None
        self._originating_event = None
        self._latest_feedback = None
        self._active_risk_level = None
        if clear_evaluation:
            self._latest_goal_evaluation = None


demo_store = DemoStore()
