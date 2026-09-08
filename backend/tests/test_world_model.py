import os

os.environ["MOCK_MODE"] = "true"

from fastapi.testclient import TestClient

from app.agent.world_model import WorldModelBuilder
from app.data.history_loader import history_context
from app.data.presets import PRESET_BUILDERS, preset_event
from app.main import app
from app.schemas.models import CareEvent


builder = WorldModelBuilder()
client = TestClient(app)


def test_stable_family_fall_world_state_keeps_both_people_and_marks_bedroom():
    context = history_context("family_30d_stable")
    child_before = context.people["child_xiaoyu"].location
    event = CareEvent(type="sensor", source="fall_detector", target_person_id="elder_li", data={"detected": True, "location": "bedroom"})
    world = builder.build(context, event)
    assert set(world.people) >= {"elder_li", "child_xiaoyu"}
    assert world.people["elder_li"].status == "suspected_fall"
    assert world.people["child_xiaoyu"].status == "normal"
    assert world.people["child_xiaoyu"].location == child_before
    assert world.rooms["bedroom"].risk_indicator == "high"
    assert world.robot and world.robot.location == "living_room" and world.robot.status == "ready"
    assert world.sensors["fall_detector"].status == "triggered"
    assert context.people["elder_li"].status == "normal"
    assert context.sensors["fall_detector"].status == "normal"


def test_child_door_event_only_changes_child_and_entrance_interpretation():
    context = history_context("family_30d_stable")
    elder_before = context.people["elder_li"].model_dump()
    child_location_before = context.people["child_xiaoyu"].location
    event = CareEvent(type="sensor", source="door_sensor", target_person_id="child_xiaoyu", data={"open": True, "location": "entrance"})
    world = builder.build(context, event)
    assert world.people["child_xiaoyu"].status == "safety_concern"
    assert world.people["child_xiaoyu"].location == child_location_before
    assert world.people["elder_li"].status == elder_before["status"]
    assert world.people["elder_li"].location == elder_before["location"]
    assert world.rooms["entrance"].risk_indicator == "concern"
    assert all(area.location == "entrance" for area in world.risk_areas)


def test_watch_inactivity_requests_confirmation_without_diagnosis():
    context = history_context("family_7d_normal")
    event = CareEvent(type="sensor", source="watch_activity", target_person_id="elder_li", data={"still_minutes": 45, "acknowledged": False, "location": "bedroom"})
    world = builder.build(context, event)
    assert world.people["elder_li"].status == "needs_confirmation"
    assert world.people["elder_li"].responsive == "unknown"
    serialized = world.model_dump_json()
    assert "疾病" not in serialized and "diagnosis" not in serialized


def test_device_offline_is_reflected_without_planning_actions():
    context = history_context("family_30d_stable")
    event = CareEvent(type="device", source="child_watch", target_person_id=None, data={"online": False})
    world = builder.build(context, event)
    assert world.devices["child_watch"].online is False
    assert world.devices["child_watch"].status == "offline"
    assert world.risk_areas == []


def test_world_state_can_be_built_without_an_event():
    context = history_context("family_30d_stable")
    world = builder.build(context, None)
    assert world.active_event is None
    assert set(world.rooms) >= {"bedroom", "living_room", "entrance", "kitchen"}
    assert world.risk_areas == []


def test_cold_start_builds_without_profile_or_memory_history():
    context = history_context("family_cold_start")
    world = builder.build(context)
    assert set(world.people) == {"elder_li", "child_xiaoyu"}
    assert all(person.status == "normal" for person in world.people.values())
    assert sum(len(person.episodic_memory) for person in context.people.values()) == 0


def test_all_legacy_presets_build_world_state():
    for preset_id, context_builder in PRESET_BUILDERS.items():
        world = builder.build(context_builder(), preset_event(preset_id))
        assert set(world.people) >= {"elder_li", "child_xiaoyu"}
        assert world.active_event is not None


def test_agent_response_contains_world_state_and_keeps_existing_fall_flow():
    assert client.post("/api/demo/histories/family_30d_stable/load").status_code == 200
    response = client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "fall_detector", "target_person_id": "elder_li", "data": {"detected": True, "location": "bedroom"}}})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["world_state"]["people"]["elder_li"]["status"] == "suspected_fall"
    assert body["decision"]["risk_level"] == "high"
    assert {action["target"] for action in body["decision"]["actions"] if action["target"]} == {"robot", "watch", "phone"}
