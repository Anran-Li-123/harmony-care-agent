from __future__ import annotations

from copy import deepcopy

from app.schemas.models import (
    CareEvent,
    ContextState,
    DeviceState,
    EnvironmentState,
    Episode,
    KnowledgeItem,
    ProfileEntry,
    SensorState,
)


BASE_KNOWLEDGE = [
    KnowledgeItem(
        id="kb_fall",
        title="跌倒应急规则",
        content="跌倒或疑似跌倒时，优先进行现场确认、手表震动提醒与家属通知；不要仅依赖语言模型判断。",
        tags=["fall", "safety", "robot", "watch"],
    ),
    KnowledgeItem(
        id="kb_door",
        title="儿童门口安全规则",
        content="儿童独处且门磁触发时，机器人应在安全距离观察并提醒儿童不要开门，同时通知家长。",
        tags=["child", "door", "safety"],
    ),
    KnowledgeItem(
        id="kb_companion",
        title="日常陪伴原则",
        content="低风险陪伴优先尊重用户偏好、提供选择，不升级为紧急报警。",
        tags=["companion", "preference"],
    ),
    KnowledgeItem(
        id="kb_watch_confirm",
        title="可穿戴状态确认规则",
        content="手表活动或位置状态异常时，先请求本人或监护人确认；演示数据不能用于疾病诊断。",
        tags=["watch", "watch_activity", "watch_geofence", "wearable", "safety"],
    ),
    KnowledgeItem(
        id="kb_device_fallback",
        title="终端离线降级规则",
        content="一个终端离线时，应优先使用仍在线的家庭终端提示并保留待重试记录。",
        tags=["device", "offline", "watch", "phone", "robot"],
    ),
]


def _devices(robot_location: str = "living_room") -> dict[str, DeviceState]:
    return {
        "robot": DeviceState(device_id="robot_01", device_type="robot", name="陪伴机器人", online=True, battery=82, location=robot_location),
        "watch": DeviceState(device_id="elder_watch_01", device_type="watch", name="老人手表", online=True, battery=68, wearing=True, owner="李爷爷", owner_person_id="elder_li"),
        "child_watch": DeviceState(device_id="child_watch_01", device_type="watch", name="儿童手表", online=True, battery=81, wearing=True, owner="小宇", owner_person_id="child_xiaoyu"),
        "phone": DeviceState(device_id="guardian_phone_01", device_type="phone", name="监护人手机", online=True, battery=74, owner="家属", owner_person_id="guardian"),
        "bedroom_light_01": DeviceState(device_id="bedroom_light_01", device_type="light", name="卧室灯", online=True, location="bedroom", state={"power": "off", "brightness": 0}),
        "hallway_light_01": DeviceState(device_id="hallway_light_01", device_type="light", name="通道灯", online=True, location="entrance", state={"power": "off", "brightness": 0}),
        "door_lock_01": DeviceState(device_id="door_lock_01", device_type="door_lock", name="玄关门锁", online=True, location="entrance", state={"locked": True}),
        "smart_screen_01": DeviceState(device_id="smart_screen_01", device_type="smart_screen", name="客厅智慧屏", online=True, location="living_room", state={"display": "idle"}),
    }


def _sensors() -> dict[str, SensorState]:
    return {
        "fall_detector": SensorState(id="fall_detector", label="跌倒感知器", location="bedroom"),
        "door_sensor": SensorState(id="door_sensor", label="门磁", location="entrance"),
        "motion_sensor": SensorState(id="motion_sensor", label="活动传感器", location="living_room"),
        "watch_activity": SensorState(id="watch_activity", label="手表活动状态", location="wearable"),
        "watch_geofence": SensorState(id="watch_geofence", label="手表安全区", location="wearable"),
    }


def new_user_context() -> ContextState:
    return ContextState(
        active_preset="new-user",
        knowledge_base=deepcopy(BASE_KNOWLEDGE),
        devices=_devices("entrance"),
        sensors=_sensors(),
        environment=EnvironmentState(
            lighting="bright",
            time_of_day="morning",
            occupancy={"entrance": ["grandpa"], "living_room": ["robot"]},
            notes=["新用户，尚无长期画像"],
        ),
    )


def night_fall_context() -> ContextState:
    return ContextState(
        active_preset="night-fall",
        knowledge_base=deepcopy(BASE_KNOWLEDGE),
        devices=_devices("living_room"),
        sensors=_sensors(),
        environment=EnvironmentState(
            lighting="dark",
            time_of_day="night",
            home_mode="elder-care",
            occupancy={"bedroom": ["grandpa"], "living_room": ["robot"]},
            notes=["老人独自在家", "夜间看护模式"],
        ),
        user_profile={
            "preferred_name": ProfileEntry(field="preferred_name", value="李爷爷", confidence=1, source_type="explicit", sources=["episode_intro"]),
            "living_situation": ProfileEntry(field="living_situation", value="夜间独处", confidence=0.9, source_type="admin", sources=["home_setup"]),
        },
        episodic_memory=[
            Episode(id="episode_sleep", person="grandpa", event="21:30 进入夜间休息", location="bedroom", result="手表佩戴正常", importance="normal")
        ],
    )


def child_door_context() -> ContextState:
    return ContextState(
        active_preset="child-door",
        knowledge_base=deepcopy(BASE_KNOWLEDGE),
        devices=_devices("living_room"),
        sensors=_sensors(),
        environment=EnvironmentState(
            lighting="bright",
            time_of_day="afternoon",
            home_mode="child-care",
            occupancy={"living_room": ["child", "robot"]},
            notes=["儿童独自在家", "家长外出"],
        ),
        user_profile={
            "preferred_name": ProfileEntry(field="preferred_name", value="小安", confidence=1, source_type="explicit", sources=["family_setup"]),
            "guardian_status": ProfileEntry(field="guardian_status", value="家长外出", confidence=1, source_type="admin", sources=["family_setup"]),
        },
    )


def companion_context() -> ContextState:
    return ContextState(
        active_preset="companion",
        knowledge_base=deepcopy(BASE_KNOWLEDGE),
        devices=_devices("living_room"),
        sensors=_sensors(),
        environment=EnvironmentState(
            lighting="warm",
            time_of_day="afternoon",
            occupancy={"living_room": ["grandpa", "robot"]},
            notes=["日常陪伴模式"],
        ),
        user_profile={
            "preferred_name": ProfileEntry(field="preferred_name", value="李爷爷", confidence=1, source_type="explicit", sources=["episode_intro"]),
            "preferred_entertainment": ProfileEntry(field="preferred_entertainment", value="京剧", confidence=0.88, source_type="inferred", sources=["episode_12", "episode_18", "episode_26"]),
        },
        episodic_memory=[
            Episode(id="episode_26", person="grandpa", event="主动播放梅派京剧", location="living_room", result="持续收听 35 分钟"),
        ],
    )


def habit_change_context() -> ContextState:
    return ContextState(
        active_preset="habit-change",
        knowledge_base=deepcopy(BASE_KNOWLEDGE),
        devices=_devices("living_room"),
        sensors=_sensors(),
        environment=EnvironmentState(
            lighting="dim",
            time_of_day="late-evening",
            occupancy={"living_room": ["grandpa", "robot"]},
            notes=["正在观察近期作息变化"],
        ),
        user_profile={
            "preferred_name": ProfileEntry(field="preferred_name", value="李爷爷", confidence=1, source_type="explicit", sources=["episode_intro"]),
            "sleep_time": ProfileEntry(field="sleep_time", value="21:30", confidence=0.72, source_type="inferred", sources=["historic_sleep"]),
        },
        episodic_memory=[
            Episode(id="episode_late_1", person="grandpa", event="22:35 仍在客厅活动", location="living_room", result="正常", importance="normal"),
            Episode(id="episode_late_2", person="grandpa", event="22:50 与机器人聊天", location="living_room", result="正常", importance="normal"),
            Episode(id="episode_late_3", person="grandpa", event="23:05 检测到持续活动", location="living_room", result="正常", importance="normal"),
        ],
    )


def elder_watch_inactive_context() -> ContextState:
    state = ContextState(
        active_preset="elder-watch-inactive",
        knowledge_base=deepcopy(BASE_KNOWLEDGE),
        devices=_devices("living_room"),
        sensors=_sensors(),
        environment=EnvironmentState(
            lighting="dim",
            time_of_day="evening",
            home_mode="elder-care",
            occupancy={"bedroom": ["grandpa"], "living_room": ["robot"]},
            notes=["老人独自在家", "手表连续佩戴中"],
        ),
        user_profile={
            "preferred_name": ProfileEntry(field="preferred_name", value="李爷爷", confidence=1, source_type="explicit", sources=["episode_intro"]),
            "usual_activity": ProfileEntry(field="usual_activity", value="晚饭后在客厅活动", confidence=0.78, source_type="inferred", sources=["routine_1", "routine_2", "routine_3"]),
        },
        episodic_memory=[
            Episode(id="routine_3", person="grandpa", event="昨日 19:10 在客厅散步", location="living_room", result="正常", importance="normal")
        ],
    )
    state.sensors["watch_activity"].status = "triggered"
    state.sensors["watch_activity"].value = {"still_minutes": 45, "acknowledged": False}
    return state


def child_safe_zone_context() -> ContextState:
    state = child_door_context()
    state.active_preset = "child-safe-zone"
    state.environment.occupancy = {"living_room": ["robot"]}
    state.environment.notes = ["儿童佩戴手表", "家长已设置家庭安全区"]
    state.sensors["watch_geofence"].status = "triggered"
    state.sensors["watch_geofence"].value = {"inside": False, "zone": "家庭安全区", "last_seen": "小区公共区域"}
    return state


def device_offline_context() -> ContextState:
    state = companion_context()
    state.active_preset = "device-offline"
    state.devices["watch"].online = False
    state.devices["watch"].status = "offline"
    state.environment.notes = ["日常看护模式", "手表连接已中断"]
    return state


PRESET_BUILDERS = {
    "new-user": new_user_context,
    "night-fall": night_fall_context,
    "elder-watch-inactive": elder_watch_inactive_context,
    "child-door": child_door_context,
    "child-safe-zone": child_safe_zone_context,
    "companion": companion_context,
    "habit-change": habit_change_context,
    "device-offline": device_offline_context,
}

PRESET_METADATA = [
    {"id": "new-user", "name": "01 · 全新老人首次交流", "description": "空记忆与空画像，从明确自我介绍开始学习", "event": "我叫李建国，你叫我李爷爷就行。", "tone": "cyan"},
    {"id": "night-fall", "name": "02 · 老人夜间疑似跌倒", "description": "无对话，跌倒传感器触发安全协同", "event": "卧室跌倒感知器触发", "tone": "red"},
    {"id": "elder-watch-inactive", "name": "03 · 老人手表长时静止", "description": "手表活动异常，请求确认而不作医疗判断", "event": "手表检测到 45 分钟静止且未确认", "tone": "amber"},
    {"id": "child-door", "name": "04 · 儿童独处门磁开启", "description": "儿童独处时门磁打开，提醒并通知家长", "event": "入口门磁打开", "tone": "red"},
    {"id": "child-safe-zone", "name": "05 · 儿童离开安全区", "description": "儿童手表位置变化，通知家长进行确认", "event": "儿童手表离开家庭安全区", "tone": "amber"},
    {"id": "companion", "name": "06 · 老人日常陪伴", "description": "依据稳定偏好提供陪伴，不升级报警", "event": "我一个人有点无聊。", "tone": "violet"},
    {"id": "habit-change", "name": "07 · 作息习惯逐渐变化", "description": "多条时间记录形成证据后谨慎更新画像", "event": "系统汇总近期晚间活动记录", "tone": "teal"},
    {"id": "device-offline", "name": "08 · 终端离线降级", "description": "手表离线后改由机器人与手机协同", "event": "手表连接中断", "tone": "slate"},
]


def preset_context(preset_id: str) -> ContextState:
    try:
        return PRESET_BUILDERS[preset_id]()
    except KeyError as exc:
        raise ValueError(f"未知 Preset：{preset_id}") from exc


def preset_event(preset_id: str) -> CareEvent:
    common = {"person": "grandpa"}
    events = {
        "new-user": CareEvent(type="conversation", source="user_voice", data={"text": "我叫李建国，你叫我李爷爷就行。", "preferred_name": "李爷爷", "location": "entrance"}, **common),
        "night-fall": CareEvent(type="sensor", source="fall_detector", data={"detected": True, "location": "bedroom"}, **common),
        "elder-watch-inactive": CareEvent(type="sensor", source="watch_activity", data={"still_minutes": 45, "acknowledged": False, "location": "bedroom"}, **common),
        "child-door": CareEvent(type="sensor", source="door_sensor", person="child", data={"open": True, "location": "entrance"}),
        "child-safe-zone": CareEvent(type="sensor", source="watch_geofence", person="child", data={"inside": False, "zone": "家庭安全区", "last_seen": "小区公共区域"}),
        "companion": CareEvent(type="conversation", source="user_voice", data={"text": "我一个人有点无聊。", "location": "living_room"}, **common),
        "habit-change": CareEvent(type="manual", source="profile_observer", data={"kind": "sleep_pattern_review", "evidence_count": 3}, **common),
        "device-offline": CareEvent(type="device", source="watch", data={"online": False, "reason": "connection_lost"}, **common),
    }
    return events[preset_id]
