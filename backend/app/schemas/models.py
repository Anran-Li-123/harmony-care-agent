from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


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


class ContextState(BaseModel):
    working_memory: list[WorkingMemoryItem] = Field(default_factory=list)
    episodic_memory: list[Episode] = Field(default_factory=list)
    user_profile: dict[str, ProfileEntry] = Field(default_factory=dict)
    knowledge_base: list[KnowledgeItem] = Field(default_factory=list)
    devices: dict[str, DeviceState] = Field(default_factory=dict)
    sensors: dict[str, SensorState] = Field(default_factory=dict)
    environment: EnvironmentState = Field(default_factory=EnvironmentState)
    active_preset: str = "new-user"


class CareEvent(BaseModel):
    id: str = Field(default_factory=lambda: f"event_{uuid4().hex[:8]}")
    type: Literal["sensor", "conversation", "device", "environment", "manual"]
    source: str
    timestamp: str = Field(default_factory=now_iso)
    person: str = "unknown"
    data: dict[str, Any] = Field(default_factory=dict)


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
    schema_version: Literal["1.0"] = "1.0"
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
