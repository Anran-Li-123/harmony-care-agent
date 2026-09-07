from __future__ import annotations

from copy import deepcopy

from app.data.presets import preset_context
from app.schemas.models import AgentDecision, ContextState


class DemoStore:
    """In-memory store behind interfaces that can later target Redis/PostgreSQL."""

    def __init__(self) -> None:
        self._context = preset_context("new-user")
        self._decisions: dict[str, AgentDecision] = {}

    def context(self) -> ContextState:
        return deepcopy(self._context)

    def replace_context(self, context: ContextState) -> ContextState:
        self._context = deepcopy(context)
        return self.context()

    def reset(self, preset_id: str = "new-user") -> ContextState:
        self._context = preset_context(preset_id)
        self._decisions = {}
        return self.context()

    def remember_decision(self, decision: AgentDecision) -> None:
        self._decisions[decision.decision_id] = deepcopy(decision)

    def decision(self, decision_id: str) -> AgentDecision | None:
        value = self._decisions.get(decision_id)
        return deepcopy(value) if value else None


demo_store = DemoStore()

