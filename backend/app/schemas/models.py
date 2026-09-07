from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.schemas.compatibility import legacy_context_to_household, legacy_event_to_target, legacy_person_id


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ActionTarget(str, Enum):
    ROBOT = "robot"
    WATCH = "watch"
    PHONE = "phone"


class ProfileEntry(BaseModel):
    field: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    source_type: Literal["explicit", "inferred", "admin", "trusted_device"]
    sources: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)


class WorkingMemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: f"work_{uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=now_iso)
    kind: str
    content: str
    expires_hint: str = "当前会话"


class Episode(BaseModel):
    id: str = Field(default_factory=lambda: f"episode_{uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=now_iso)
    person: str = "unknown"
    event: str
    location: str = "unknown"
    actions: list[str] = Field(default_factory=list)
    result: str = "待确认"
    importance: Literal["low", "normal", "high"] = "normal"


class DeviceState(BaseModel):
    id: str
    kind: ActionTarget
    online: bool = True
    battery: int = Field(default=100, ge=0, le=100)
    location: str | None = None
    owner: str | None = None
    wearing: bool | None = None
    latest_action: str = "待命"
    status: str = "ready"
    speech: str | None = None
    latest_notification: str | None = None


class SensorState(BaseModel):
    id: str
    label: str
    location: str
    status: Literal["normal", "triggered", "offline"] = "normal"
    value: Any = None
    updated_at: str = Field(default_factory=now_iso)


class EnvironmentState(BaseModel):
    lighting: str = "bright"
    time_of_day: str = "daytime"
    temperature_c: float = 24.0
    noise_level: str = "quiet"
    home_mode: str = "normal"
    occupancy: dict[str, list[str]] = Field(default_factory=dict)
    door_state: str = "closed"
    notes: list[str] = Field(default_factory=list)


class KnowledgeItem(BaseModel):
    id: str = Field(default_factory=lambda: f"kb_{uuid4().hex[:8]}")
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)


class HouseholdContext(BaseModel):
    household_id: str = "family_001"
    name: str = "示例家庭"
    household_memory: list[WorkingMemoryItem] = Field(default_factory=list)


class PersonContext(BaseModel):
    person_id: str
    role: Literal["elder", "child"]
    name: str
    location: str | None = None
    status: str = "normal"
    working_memory: list[WorkingMemoryItem] = Field(default_factory=list)
    episodic_memory: list[Episode] = Field(default_factory=list)
    user_profile: dict[str, ProfileEntry] = Field(default_factory=dict)


class ContextState(BaseModel):
    schema_version: Literal["2.0"] = "2.0"
    household: HouseholdContext = Field(default_factory=HouseholdContext)
    people: dict[str, PersonContext] = Field(default_factory=dict)
    active_history: str | None = None
    # v1 fields remain as a compatibility projection for old clients/uploads.
    working_memory: list[WorkingMemoryItem] = Field(default_factory=list)
    episodic_memory: list[Episode] = Field(default_factory=list)
    user_profile: dict[str, ProfileEntry] = Field(default_factory=dict)
    knowledge_base: list[KnowledgeItem] = Field(default_factory=list)
    devices: dict[str, DeviceState] = Field(default_factory=dict)
    sensors: dict[str, SensorState] = Field(default_factory=dict)
    environment: EnvironmentState = Field(default_factory=EnvironmentState)
    active_preset: str = "new-user"

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_context(cls, value: Any) -> Any:
        return legacy_context_to_household(value)

    @model_validator(mode="after")
    def validate_household_people(self) -> "ContextState":
        for key, person in self.people.items():
            if key != person.person_id:
                raise ValueError(f"people key {key!r} 必须与 person_id 一致")
        roles = {person.role for person in self.people.values()}
        if not {"elder", "child"}.issubset(roles):
            raise ValueError("家庭 Context 必须同时包含至少一名老人和一名儿童")
        if not self.working_memory and not self.episodic_memory and not self.user_profile:
            elder = next((person for person in self.people.values() if person.role == "elder"), None)
            if elder:
                self.sync_legacy_projection(elder.person_id)
        return self

    def target_person(self, person_id: str | None) -> PersonContext | None:
        return self.people.get(legacy_person_id(person_id) or "")

    def sync_legacy_projection(self, person_id: str | None) -> None:
        person = self.target_person(person_id)
        if person is None:
            self.working_memory = []
            self.episodic_memory = []
            self.user_profile = {}
            return
        self.working_memory = list(person.working_memory)
        self.episodic_memory = list(person.episodic_memory)
        self.user_profile = dict(person.user_profile)


class CareEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"event_{uuid4().hex[:8]}")
    type: Literal["sensor", "conversation", "device", "environment", "manual"]
    source: str
    timestamp: str = Field(default_factory=now_iso)
    target_person_id: str | None = None
    person: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_person(cls, value: Any) -> Any:
        return legacy_event_to_target(value)


class DeviceAction(BaseModel):
    target: ActionTarget
    action: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    rationale: str = ""


class MemoryCandidate(BaseModel):
    type: Literal["working", "episodic"]
    reason: str
    preview: str


class ProfileCandidate(BaseModel):
    field: str
    value: Any
    confidence: float = Field(ge=0, le=1)
    source_type: Literal["explicit", "inferred", "admin", "trusted_device"]
    sources: list[str] = Field(default_factory=list)
    rationale: str
    allowed: bool = True


class ProfileChange(BaseModel):
    field: str
    before: Any = None
    after: Any
    confidence: float
    explanation: str


class TimelineItem(BaseModel):
    id: str = Field(default_factory=lambda: f"time_{uuid4().hex[:8]}")
    timestamp: str = Field(default_factory=now_iso)
    title: str
    detail: str
    stage: str
    tone: Literal["neutral", "info", "success", "warning", "danger"] = "neutral"


class AgentDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: f"decision_{uuid4().hex[:10]}")
    risk_level: RiskLevel
    summary: str
    evidence: list[str] = Field(default_factory=list)
    retrieved_knowledge: list[str] = Field(default_factory=list)
    actions: list[DeviceAction] = Field(default_factory=list)
    memory_updates: list[MemoryCandidate] = Field(default_factory=list)
    profile_candidates: list[ProfileCandidate] = Field(default_factory=list)
    profile_changes: list[ProfileChange] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)
    llm_mode: Literal["mock", "openai-compatible"] = "mock"


class TriggerRequest(BaseModel):
    event: CareEvent


class TriggerResponse(BaseModel):
    context: ContextState
    decision: AgentDecision


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=2, max_length=500)


class ScenarioOption(BaseModel):
    id: str
    label: str
    description: str
    compatible_personas: list[Literal["elder", "child"]] = Field(default_factory=lambda: ["elder", "child"])
    tone: str = "cyan"


class ScenarioOptions(BaseModel):
    personas: list[ScenarioOption]
    memory_packs: list[ScenarioOption]
    state_packs: list[ScenarioOption]
    trigger_packs: list[ScenarioOption]


class ScenarioGenerationRequest(BaseModel):
    persona_pack: Literal["elder", "child"] = "elder"
    memory_pack: str = "blank"
    state_pack: str = "daytime-normal"
    trigger_pack: str = "elder-intro"
    prompt: str | None = Field(default=None, max_length=500)


class ScenarioDraft(BaseModel):
    # Existing scenario endpoints keep emitting 1.0; v2 envelopes are accepted for new household data.
    schema_version: Literal["1.0", "2.0"] = "1.0"
    id: str = Field(default_factory=lambda: f"scenario_{uuid4().hex[:8]}")
    title: str
    description: str
    source: Literal["preset", "template", "ai", "fallback", "upload"] = "template"
    context: ContextState
    event: CareEvent
    warnings: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    context: ContextState
    message: str
    event: CareEvent | None = None
    scenario: ScenarioDraft | None = None
