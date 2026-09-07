from __future__ import annotations

from copy import deepcopy

from app.data.presets import preset_context
from app.schemas.models import AgentDecision, AgentPlan, CareGoal, CareGoalStatus, ContextState


class DemoStore:
    """In-memory store behind interfaces that can later target Redis/PostgreSQL."""

    def __init__(self) -> None:
        self._context = preset_context("new-user")
        self._decisions: dict[str, AgentDecision] = {}
        self._active_goal: CareGoal | None = None
        self._active_plan: AgentPlan | None = None

    def context(self) -> ContextState:
        return deepcopy(self._context)

    def replace_context(self, context: ContextState) -> ContextState:
        self._context = deepcopy(context)
        self._active_goal = None
        self._active_plan = None
        return self.context()

    def reset(self, preset_id: str = "new-user") -> ContextState:
        self._context = preset_context(preset_id)
        self._decisions = {}
        self._active_goal = None
        self._active_plan = None
        return self.context()

    def remember_decision(self, decision: AgentDecision) -> None:
        self._decisions[decision.decision_id] = deepcopy(decision)
        if decision.care_goal and decision.care_goal.status in {CareGoalStatus.ACTIVE, CareGoalStatus.AWAITING_FEEDBACK}:
            self._active_goal = deepcopy(decision.care_goal)
            self._active_plan = deepcopy(decision.agent_plan)
        else:
            self._active_goal = None
            self._active_plan = None

    def decision(self, decision_id: str) -> AgentDecision | None:
        value = self._decisions.get(decision_id)
        return deepcopy(value) if value else None

    def active_goal(self) -> CareGoal | None:
        return deepcopy(self._active_goal)

    def active_plan(self) -> AgentPlan | None:
        return deepcopy(self._active_plan)


demo_store = DemoStore()
