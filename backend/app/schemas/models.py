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


class DeviceType(str, Enum):
    ROBOT = "robot"
    WATCH = "watch"
    PHONE = "phone"
    LIGHT = "light"
    DOOR_LOCK = "door_lock"
    SMART_SCREEN = "smart_screen"


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


DEVICE_CAPABILITIES: dict[str, list[str]] = {
    "robot": ["navigate_to", "speak", "observe", "follow", "wait", "play_audio"],
    "watch": ["vibrate", "show_message", "request_confirmation"],
    "phone": ["push_notification", "request_confirmation", "show_status"],
    "light": ["switch", "set_brightness"],
    "door_lock": ["lock", "get_status"],
    "smart_screen": ["show_message", "display_status", "start_call"],
}


class HarmonyDevice(BaseModel):
    device_id: str
    device_type: DeviceType
    name: str
    online: bool = True
    capabilities: list[str] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    owner_person_id: str | None = None
    # Compatibility fields used by v1 Context and the existing UI.
    id: str
    kind: DeviceType
    battery: int = Field(default=100, ge=0, le=100)
    location: str | None = None
    owner: str | None = None
    wearing: bool | None = None
    latest_action: str = "待命"
    status: str = "ready"
    speech: str | None = None
    latest_notification: str | None = None

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_device(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        upgraded = dict(value)
        upgraded.setdefault("device_id", upgraded.get("id"))
        upgraded.setdefault("id", upgraded.get("device_id"))
        upgraded.setdefault("device_type", upgraded.get("kind"))
        upgraded.setdefault("kind", upgraded.get("device_type"))
        raw_device_type = upgraded.get("device_type", "")
        device_type = raw_device_type.value if isinstance(raw_device_type, DeviceType) else str(raw_device_type)
        upgraded.setdefault("name", upgraded.get("id") or device_type)
        upgraded.setdefault("capabilities", list(DEVICE_CAPABILITIES.get(device_type, [])))
        owner = upgraded.get("owner")
        if not upgraded.get("owner_person_id") and owner in {"李爷爷", "李建国"}:
            upgraded["owner_person_id"] = "elder_li"
        if not upgraded.get("owner_person_id") and owner in {"小宇", "小安"}:
            upgraded["owner_person_id"] = "child_xiaoyu"
        return upgraded

    @model_validator(mode="after")
    def populate_semantic_state(self) -> "HarmonyDevice":
        self.state.setdefault("status", self.status)
        self.state.setdefault("latest_action", self.latest_action)
        if self.location is not None:
            self.state.setdefault("location", self.location)
        if self.device_type in {DeviceType.WATCH, DeviceType.PHONE, DeviceType.ROBOT}:
            self.state.setdefault("battery", self.battery)
        if self.device_type == DeviceType.LIGHT:
            self.state.setdefault("power", "off")
            self.state.setdefault("brightness", 0)
        elif self.device_type == DeviceType.DOOR_LOCK:
            self.state.setdefault("locked", True)
        elif self.device_type == DeviceType.SMART_SCREEN:
            self.state.setdefault("display", "idle")
        return self


# Existing builders/imports keep working while Context now exposes HarmonyDevice.
DeviceState = HarmonyDevice


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


class PersonWorldState(BaseModel):
    person_id: str
    role: Literal["elder", "child"]
    name: str
    location: str | None = None
    status: str = "normal"
    responsive: Literal["normal", "unknown", "responsive", "unresponsive"] = "normal"


class RobotWorldState(BaseModel):
    device_id: str
    location: str | None = None
    online: bool = True
    status: str = "ready"


class RoomWorldState(BaseModel):
    room_id: str
    occupied_by: list[str] = Field(default_factory=list)
    lighting: str = "normal"
    risk_indicator: Literal["normal", "concern", "high"] = "normal"


class DeviceWorldState(BaseModel):
    device_id: str
    device_type: str
    name: str
    location: str | None = None
    online: bool = True
    status: str = "ready"
    state: dict[str, Any] = Field(default_factory=dict)


class SensorWorldState(BaseModel):
    sensor_id: str
    label: str
    location: str
    status: Literal["normal", "triggered", "offline"] = "normal"
    value: Any = None


class ActiveWorldEvent(BaseModel):
    event_id: str
    target_person_id: str | None = None
    type: str
    source: str
    timestamp: str


class RiskArea(BaseModel):
    location: str
    reason: str
    risk_indicator: Literal["concern", "high"]


class WorldState(BaseModel):
    timestamp: str = Field(default_factory=now_iso)
    people: dict[str, PersonWorldState] = Field(default_factory=dict)
    robot: RobotWorldState | None = None
    rooms: dict[str, RoomWorldState] = Field(default_factory=dict)
    devices: dict[str, DeviceWorldState] = Field(default_factory=dict)
    sensors: dict[str, SensorWorldState] = Field(default_factory=dict)
    environment: EnvironmentState = Field(default_factory=EnvironmentState)
    active_event: ActiveWorldEvent | None = None
    risk_areas: list[RiskArea] = Field(default_factory=list)


class ActionIntent(BaseModel):
    capability: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    reason: str = ""
    target_device_id: str | None = None
    device_type: DeviceType | None = None
    location: str | None = None
    target_person_id: str | None = None


class DeviceAction(BaseModel):
    target_device_id: str | None = None
    capability: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    reason: str = ""
    # v1 fields remain accepted; resolution is centralized in devices.compatibility.
    target: ActionTarget | None = None
    action: str | None = None
    rationale: str = ""

    @model_validator(mode="after")
    def validate_action_shape(self) -> "DeviceAction":
        if not ((self.target_device_id and self.capability) or (self.target and self.action)):
            raise ValueError("DeviceAction 必须提供 v2 device/capability 或 v1 target/action")
        if not self.reason and self.rationale:
            self.reason = self.rationale
        if not self.rationale and self.reason:
            self.rationale = self.reason
        return self


class DeviceExecutionResult(BaseModel):
    device_id: str
    capability: str
    success: bool
    message: str
    resulting_state: dict[str, Any] = Field(default_factory=dict)


class CareGoalStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    AWAITING_FEEDBACK = "awaiting_feedback"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanStepStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    AWAITING_FEEDBACK = "awaiting_feedback"


class CareGoal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid4().hex[:10]}")
    goal_type: str
    target_person_id: str | None = None
    description: str
    priority: Priority = Priority.NORMAL
    status: CareGoalStatus = CareGoalStatus.PLANNED
    requires_feedback: bool = False


class PlanCapabilityRequest(BaseModel):
    capability: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    target_location: str | None = None
    target_person_id: str | None = None
    device_type: DeviceType | None = None

    @model_validator(mode="after")
    def validate_capability(self) -> "PlanCapabilityRequest":
        allowed = {item for capabilities in DEVICE_CAPABILITIES.values() for item in capabilities}
        if self.capability not in allowed:
            raise ValueError(f"Plan capability 不在白名单：{self.capability}")
        return self


class PlanStep(BaseModel):
    step_id: str = Field(default_factory=lambda: f"step_{uuid4().hex[:8]}")
    intent: str
    description: str
    priority: Priority = Priority.NORMAL
    status: PlanStepStatus = PlanStepStatus.PLANNED
    target_location: str | None = None
    target_person_id: str | None = None
    required_capability: str | None = None
    capability_requests: list[PlanCapabilityRequest] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_primary_capability(self) -> "PlanStep":
        allowed = {item for capabilities in DEVICE_CAPABILITIES.values() for item in capabilities}
        if self.required_capability and self.required_capability not in allowed:
            raise ValueError(f"PlanStep capability 不在白名单：{self.required_capability}")
        if not self.required_capability and self.capability_requests:
            self.required_capability = self.capability_requests[0].capability
        return self


class AgentPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid4().hex[:10]}")
    goal_id: str
    summary: str
    steps: list[PlanStep] = Field(default_factory=list)


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
    execution_results: list[DeviceExecutionResult] = Field(default_factory=list)
    care_goal: CareGoal | None = None
    agent_plan: AgentPlan | None = None
    memory_updates: list[MemoryCandidate] = Field(default_factory=list)
    profile_candidates: list[ProfileCandidate] = Field(default_factory=list)
    profile_changes: list[ProfileChange] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)
    world_state: WorldState | None = None
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
