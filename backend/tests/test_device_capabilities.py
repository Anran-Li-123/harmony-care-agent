import os

os.environ["MOCK_MODE"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.data.history_loader import history_context
from app.data.presets import PRESET_BUILDERS, preset_event
from app.devices.adapters import ActionRouter
from app.devices.compatibility import legacy_device_action_to_v2
from app.devices.registry import CapabilityMatcher, DeviceRegistry
from app.main import app
from app.schemas.models import DeviceAction, DeviceType


client = TestClient(app)


def test_registry_loads_six_device_types():
    registry = DeviceRegistry(history_context("family_30d_stable").devices)
    assert {device.device_type for device in registry.all()} == {
        DeviceType.ROBOT, DeviceType.WATCH, DeviceType.PHONE, DeviceType.LIGHT, DeviceType.DOOR_LOCK, DeviceType.SMART_SCREEN,
    }


def test_capability_matcher_finds_bedroom_light():
    matcher = CapabilityMatcher(DeviceRegistry(history_context("family_30d_stable").devices))
    assert matcher.match("switch", location="bedroom").device_id == "bedroom_light_01"


def test_person_owned_watch_matching_is_isolated():
    matcher = CapabilityMatcher(DeviceRegistry(history_context("family_30d_stable").devices))
    elder = matcher.match("vibrate", target_person_id="elder_li")
    child = matcher.match("vibrate", target_person_id="child_xiaoyu")
    assert elder and elder.device_id == "elder_watch_01"
    assert child and child.device_id == "child_watch_01"


def test_offline_device_is_not_a_default_match():
    context = history_context("family_30d_stable")
    context.devices["watch"].online = False
    matcher = CapabilityMatcher(DeviceRegistry(context.devices))
    assert matcher.match("vibrate", target_person_id="elder_li") is None


@pytest.mark.parametrize(
    ("device_key", "capability", "kwargs"),
    [
        ("watch", "vibrate", {"target_person_id": "elder_li"}),
        ("phone", "push_notification", {}),
        ("smart_screen_01", "show_message", {"location": "living_room", "device_type": DeviceType.SMART_SCREEN}),
    ],
)
def test_matcher_never_selects_an_offline_key_device(device_key: str, capability: str, kwargs: dict[str, object]):
    context = history_context("family_30d_stable")
    context.devices[device_key].online = False
    context.devices[device_key].status = "offline"
    matcher = CapabilityMatcher(DeviceRegistry(context.devices))
    assert matcher.match(capability, **kwargs) is None


def test_light_switch_returns_structured_result_and_updates_context():
    context = history_context("family_30d_stable")
    action = DeviceAction(target_device_id="bedroom_light_01", capability="switch", parameters={"value": "on"}, reason="测试照明")
    result = ActionRouter().dispatch(context, [action])[0]
    assert result.success is True
    assert result.resulting_state["power"] == "on"
    assert context.devices["bedroom_light_01"].state["power"] == "on"


def test_door_lock_stays_locked():
    context = history_context("family_30d_stable")
    lock = ActionRouter().dispatch(context, [DeviceAction(target_device_id="door_lock_01", capability="lock")])[0]
    assert lock.success is True and lock.resulting_state["locked"] is True


def test_new_unlock_capability_is_rejected():
    context = history_context("family_30d_stable")
    unlock = ActionRouter().dispatch(context, [DeviceAction(target_device_id="door_lock_01", capability="unlock")])[0]
    assert unlock.success is False
    assert context.devices["door_lock_01"].state["locked"] is True


def test_legacy_action_conversion_is_centralized():
    matcher = CapabilityMatcher(DeviceRegistry(history_context("family_30d_stable").devices))
    converted = legacy_device_action_to_v2(DeviceAction(target="robot", action="move_to", parameters={"location": "bedroom"}), matcher)
    assert converted and converted.target_device_id == "robot_01" and converted.capability == "navigate_to"


def test_fall_plan_uses_lights_robot_elder_watch_and_guardian_phone():
    client.post("/api/demo/histories/family_30d_stable/load")
    body = client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "fall_detector", "target_person_id": "elder_li", "data": {"detected": True, "location": "bedroom"}}}).json()
    actions = {(action["target_device_id"], action["capability"]) for action in body["decision"]["actions"]}
    assert {("hallway_light_01", "switch"), ("bedroom_light_01", "switch"), ("robot_01", "navigate_to"), ("robot_01", "observe"), ("robot_01", "speak"), ("elder_watch_01", "vibrate"), ("guardian_phone_01", "push_notification")} <= actions
    assert all(result["success"] for result in body["decision"]["execution_results"])
    world = body["decision"]["world_state"]
    assert world["robot"]["location"] == "living_room"
    assert world["devices"]["bedroom_light_01"]["state"]["power"] == "off"
    assert world["devices"]["hallway_light_01"]["state"]["power"] == "off"
    assert body["context"]["devices"]["bedroom_light_01"]["state"]["power"] == "on"


def test_child_door_plan_uses_lock_robot_screen_child_watch_and_phone_without_unlock():
    client.post("/api/demo/histories/family_30d_stable/load")
    body = client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "door_sensor", "target_person_id": "child_xiaoyu", "data": {"open": True, "location": "entrance"}}}).json()
    actions = {(action["target_device_id"], action["capability"]) for action in body["decision"]["actions"]}
    assert {("door_lock_01", "lock"), ("robot_01", "navigate_to"), ("robot_01", "speak"), ("smart_screen_01", "show_message"), ("child_watch_01", "vibrate"), ("guardian_phone_01", "push_notification")} <= actions
    assert all(action["capability"] != "unlock" for action in body["decision"]["actions"])
    assert body["context"]["devices"]["door_lock_01"]["state"]["locked"] is True


def test_guardian_phone_offline_falls_back_to_robot_watch_and_screen():
    client.post("/api/demo/histories/family_30d_stable/load")
    body = client.post("/api/events/trigger", json={"event": {"type": "device", "source": "guardian_phone_01", "data": {"online": False}}}).json()
    device_ids = {action["target_device_id"] for action in body["decision"]["actions"]}
    assert {"robot_01", "elder_watch_01", "smart_screen_01"} <= device_ids
    assert "guardian_phone_01" not in device_ids


def test_old_presets_keep_running_with_capability_devices():
    for preset_id, context_builder in PRESET_BUILDERS.items():
        context = context_builder()
        assert len(DeviceRegistry(context.devices).by_type(DeviceType.LIGHT)) == 2
        response = client.post("/api/reset", params={"preset_id": preset_id})
        assert response.status_code == 200
        assert client.post("/api/events/trigger", json={"event": preset_event(preset_id).model_dump()}).status_code == 200


def test_static_histories_keep_valid_consistent_device_ids():
    expected_ids = {"robot_01", "elder_watch_01", "child_watch_01", "guardian_phone_01", "bedroom_light_01", "hallway_light_01", "door_lock_01", "smart_screen_01"}
    for history_id in ["family_cold_start", "family_7d_normal", "family_30d_stable"]:
        context = history_context(history_id)
        assert {device.device_id for device in context.devices.values()} == expected_ids
