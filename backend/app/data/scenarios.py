from __future__ import annotations

from copy import deepcopy

from app.data.presets import BASE_KNOWLEDGE, PRESET_METADATA, _devices, preset_context, preset_event
from app.schemas.models import (
    CareEvent,
    ContextState,
    EnvironmentState,
    Episode,
    ProfileEntry,
    ScenarioDraft,
    ScenarioGenerationRequest,
    ScenarioOption,
    ScenarioOptions,
    SensorState,
    WorkingMemoryItem,
)


PERSONAS = [
    ScenarioOption(id="elder", label="老人用户", description="以老人、陪伴与居家安全为主要上下文", compatible_personas=["elder"]),
    ScenarioOption(id="child", label="儿童用户", description="以儿童、监护人与家庭安全为主要上下文", compatible_personas=["child"], tone="violet"),
]

MEMORY_PACKS = [
    ScenarioOption(id="blank", label="完全空白", description="没有短期记忆、时间记录或用户画像"),
    ScenarioOption(id="recent", label="近期短期记忆", description="包含当前会话中刚发生的两条信息"),
    ScenarioOption(id="routine", label="连续时间记录", description="包含多天可追溯的日常事件"),
    ScenarioOption(id="stable", label="稳定用户画像", description="包含由多条证据形成的偏好与家庭设置"),
    ScenarioOption(id="changing", label="习惯变化记录", description="旧画像与近期多条新证据同时存在", compatible_personas=["elder"], tone="amber"),
]

STATE_PACKS = [
    ScenarioOption(id="daytime-normal", label="白天 · 状态正常", description="家庭终端在线，环境明亮且安静"),
    ScenarioOption(id="elder-night", label="夜间 · 老人独处", description="卧室有人，机器人位于客厅", compatible_personas=["elder"], tone="violet"),
    ScenarioOption(id="child-home-alone", label="下午 · 儿童独处", description="家长外出，开启儿童看护模式", compatible_personas=["child"], tone="amber"),
    ScenarioOption(id="wearable-alert", label="手表 · 状态变化", description="手表在线并提供活动或安全区记录", tone="amber"),
    ScenarioOption(id="device-degraded", label="终端 · 连接降级", description="手表离线，其他设备继续在线", tone="slate"),
]

TRIGGER_PACKS = [
    ScenarioOption(id="elder-intro", label="老人首次自我介绍", description="带有明确称呼偏好的新对话", compatible_personas=["elder"]),
    ScenarioOption(id="elder-companion", label="老人表达陪伴需求", description="普通对话，不触发紧急通知", compatible_personas=["elder"], tone="violet"),
    ScenarioOption(id="fall", label="跌倒感知变化", description="无对话，由卧室传感器触发", compatible_personas=["elder"], tone="red"),
    ScenarioOption(id="watch-inactive", label="手表长时静止", description="无对话，请求确认但不作医疗判断", compatible_personas=["elder"], tone="amber"),
    ScenarioOption(id="child-chat", label="儿童发起普通对话", description="低风险家庭问候", compatible_personas=["child"], tone="violet"),
    ScenarioOption(id="door-open", label="儿童独处时门开", description="无对话，由入口门磁触发", compatible_personas=["child"], tone="red"),
    ScenarioOption(id="safe-zone", label="儿童离开安全区", description="无对话，由手表位置状态触发", compatible_personas=["child"], tone="amber"),
    ScenarioOption(id="sleep-review", label="汇总近期作息", description="无新对话，由时间记录触发画像复核", compatible_personas=["elder"], tone="teal"),
    ScenarioOption(id="device-offline", label="手表连接中断", description="无对话，由设备在线状态变化触发", tone="slate"),
]

SCENARIO_OPTIONS = ScenarioOptions(
    personas=PERSONAS,
    memory_packs=MEMORY_PACKS,
    state_packs=STATE_PACKS,
    trigger_packs=TRIGGER_PACKS,
)

PRESET_PACKS: dict[str, tuple[str, str, str, str]] = {
    "new-user": ("elder", "blank", "daytime-normal", "elder-intro"),
    "night-fall": ("elder", "routine", "elder-night", "fall"),
    "elder-watch-inactive": ("elder", "routine", "wearable-alert", "watch-inactive"),
    "child-door": ("child", "stable", "child-home-alone", "door-open"),
    "child-safe-zone": ("child", "routine", "wearable-alert", "safe-zone"),
    "companion": ("elder", "stable", "daytime-normal", "elder-companion"),
    "habit-change": ("elder", "changing", "elder-night", "sleep-review"),
    "device-offline": ("elder", "stable", "device-degraded", "device-offline"),
}


def options_payload() -> ScenarioOptions:
    return SCENARIO_OPTIONS.model_copy(deep=True)


def draft_from_preset(preset_id: str, source: str = "preset") -> ScenarioDraft:
    metadata = next(item for item in PRESET_METADATA if item["id"] == preset_id)
    return ScenarioDraft(
        id=f"preset_{preset_id}",
        title=metadata["name"].split(" · ", 1)[-1],
        description=metadata["description"],
        source=source,
        context=preset_context(preset_id),
        event=preset_event(preset_id),
    )


def packs_for_preset(preset_id: str) -> dict[str, str]:
    persona, memory, state, trigger = PRESET_PACKS[preset_id]
    return {"persona_pack": persona, "memory_pack": memory, "state_pack": state, "trigger_pack": trigger}


def _lookup(options: list[ScenarioOption], option_id: str, persona: str) -> ScenarioOption:
    option = next((item for item in options if item.id == option_id), None)
    if option is None:
        raise ValueError(f"未知场景选项：{option_id}")
    if persona not in option.compatible_personas:
        raise ValueError(f"{option.label} 不适用于当前用户类型")
    return option


def _base_context(persona: str) -> ContextState:
    person = "grandpa" if persona == "elder" else "child"
    context = ContextState(
        active_preset="custom",
        knowledge_base=deepcopy(BASE_KNOWLEDGE),
        devices=_devices("living_room"),
        sensors={
            "fall_detector": SensorState(id="fall_detector", label="跌倒感知器", location="bedroom"),
            "door_sensor": SensorState(id="door_sensor", label="门磁", location="entrance"),
            "motion_sensor": SensorState(id="motion_sensor", label="活动传感器", location="living_room"),
            "watch_activity": SensorState(id="watch_activity", label="手表活动状态", location="wearable"),
            "watch_geofence": SensorState(id="watch_geofence", label="手表安全区", location="wearable"),
        },
        environment=EnvironmentState(
            lighting="bright",
            time_of_day="daytime",
            occupancy={"living_room": [person, "robot"]},
            notes=["组合生成的演示场景"],
        ),
    )
    return context


def _apply_memory(context: ContextState, persona: str, memory_pack: str) -> None:
    person = "grandpa" if persona == "elder" else "child"
    name = "李爷爷" if persona == "elder" else "小安"
    if memory_pack == "blank":
        return
    if memory_pack == "recent":
        context.working_memory = [
            WorkingMemoryItem(kind="conversation", content=f"{name}刚刚确认已在家"),
            WorkingMemoryItem(kind="environment", content="客厅活动传感器状态正常"),
        ]
        return
    if memory_pack == "routine":
        context.episodic_memory = [
            Episode(person=person, event="前日 18:40 返回家中", location="entrance", result="正常"),
            Episode(person=person, event="昨日 19:10 在客厅活动", location="living_room", result="正常"),
            Episode(person=person, event="今日按日常安排使用手表", location="living_room", result="佩戴正常"),
        ]
        context.user_profile["preferred_name"] = ProfileEntry(field="preferred_name", value=name, confidence=1, source_type="explicit", sources=["family_setup"])
        return
    if memory_pack == "stable":
        context.user_profile["preferred_name"] = ProfileEntry(field="preferred_name", value=name, confidence=1, source_type="explicit", sources=["family_setup"])
        if persona == "elder":
            context.user_profile["preferred_entertainment"] = ProfileEntry(field="preferred_entertainment", value="京剧", confidence=.88, source_type="inferred", sources=["episode_12", "episode_18", "episode_26"])
            context.episodic_memory = [Episode(id="episode_26", person=person, event="主动播放梅派京剧", location="living_room", result="持续收听 35 分钟")]
        else:
            context.user_profile["guardian_status"] = ProfileEntry(field="guardian_status", value="家长外出", confidence=1, source_type="admin", sources=["family_setup"])
            context.episodic_memory = [Episode(person=person, event="放学后按时回到家中", location="entrance", result="家长已收到通知")]
        return
    if memory_pack == "changing":
        context.user_profile = {
            "preferred_name": ProfileEntry(field="preferred_name", value="李爷爷", confidence=1, source_type="explicit", sources=["episode_intro"]),
            "sleep_time": ProfileEntry(field="sleep_time", value="21:30", confidence=.72, source_type="inferred", sources=["historic_sleep"]),
        }
        context.episodic_memory = [
            Episode(id="episode_late_1", person=person, event="22:35 仍在客厅活动", location="living_room", result="正常"),
            Episode(id="episode_late_2", person=person, event="22:50 与机器人聊天", location="living_room", result="正常"),
            Episode(id="episode_late_3", person=person, event="23:05 检测到持续活动", location="living_room", result="正常"),
        ]


def _apply_state(context: ContextState, persona: str, state_pack: str) -> None:
    person = "grandpa" if persona == "elder" else "child"
    if state_pack == "daytime-normal":
        context.environment = EnvironmentState(lighting="bright", time_of_day="daytime", temperature_c=24, noise_level="quiet", occupancy={"living_room": [person, "robot"]}, notes=["设备状态正常"])
    elif state_pack == "elder-night":
        context.environment = EnvironmentState(lighting="dark", time_of_day="night", temperature_c=23, noise_level="quiet", home_mode="elder-care", occupancy={"bedroom": ["grandpa"], "living_room": ["robot"]}, notes=["老人独自在家", "夜间看护模式"])
    elif state_pack == "child-home-alone":
        context.environment = EnvironmentState(lighting="bright", time_of_day="afternoon", temperature_c=24, noise_level="normal", home_mode="child-care", occupancy={"living_room": ["child", "robot"]}, notes=["儿童独自在家", "家长外出"])
    elif state_pack == "wearable-alert":
        context.environment.notes = ["手表连续佩戴中", "等待处理可穿戴设备状态变化"]
    elif state_pack == "device-degraded":
        context.devices["watch"].online = False
        context.devices["watch"].status = "offline"
        context.environment.notes = ["手表连接已中断", "其他家庭终端在线"]


def _event_for(persona: str, trigger_pack: str) -> CareEvent:
    person = "grandpa" if persona == "elder" else "child"
    events = {
        "elder-intro": CareEvent(type="conversation", source="user_voice", person="grandpa", data={"text": "我叫李建国，你叫我李爷爷就行。", "preferred_name": "李爷爷", "location": "living_room"}),
        "elder-companion": CareEvent(type="conversation", source="user_voice", person="grandpa", data={"text": "我一个人有点无聊。", "location": "living_room"}),
        "fall": CareEvent(type="sensor", source="fall_detector", person="grandpa", data={"detected": True, "location": "bedroom"}),
        "watch-inactive": CareEvent(type="sensor", source="watch_activity", person="grandpa", data={"still_minutes": 45, "acknowledged": False, "location": "bedroom"}),
        "child-chat": CareEvent(type="conversation", source="user_voice", person="child", data={"text": "我已经到家了。", "location": "living_room"}),
        "door-open": CareEvent(type="sensor", source="door_sensor", person="child", data={"open": True, "location": "entrance"}),
        "safe-zone": CareEvent(type="sensor", source="watch_geofence", person="child", data={"inside": False, "zone": "家庭安全区", "last_seen": "小区公共区域"}),
        "sleep-review": CareEvent(type="manual", source="profile_observer", person="grandpa", data={"kind": "sleep_pattern_review", "evidence_count": 3}),
        "device-offline": CareEvent(type="device", source="watch", person=person, data={"online": False, "reason": "connection_lost"}),
    }
    return events[trigger_pack]


def compose_scenario(request: ScenarioGenerationRequest, source: str = "template", warnings: list[str] | None = None) -> ScenarioDraft:
    persona = _lookup(PERSONAS, request.persona_pack, request.persona_pack)
    memory = _lookup(MEMORY_PACKS, request.memory_pack, request.persona_pack)
    state = _lookup(STATE_PACKS, request.state_pack, request.persona_pack)
    trigger = _lookup(TRIGGER_PACKS, request.trigger_pack, request.persona_pack)
    context = _base_context(request.persona_pack)
    _apply_memory(context, request.persona_pack, request.memory_pack)
    _apply_state(context, request.persona_pack, request.state_pack)
    event = _event_for(request.persona_pack, request.trigger_pack)
    if event.source in context.sensors:
        context.sensors[event.source].value = event.data
    context.environment.notes.append(f"数据组合：{memory.label} / {state.label}")
    return ScenarioDraft(
        title=f"{persona.label} · {trigger.label}",
        description=f"{memory.description}；{state.description}。",
        source=source,
        context=context,
        event=event,
        warnings=warnings or [],
    )
