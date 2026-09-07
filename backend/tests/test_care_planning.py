import os

os.environ["MOCK_MODE"] = "true"

from fastapi.testclient import TestClient

from app.agent.llm import MockLLMProvider, provider_for
from app.config import get_settings
from app.data.history_loader import history_context
from app.data.presets import PRESET_BUILDERS, preset_event
from app.main import app
from app.services.store import demo_store


client = TestClient(app)


def run_fall() -> dict:
    client.post("/api/demo/histories/family_30d_stable/load")
    return client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "fall_detector", "target_person_id": "elder_li", "data": {"detected": True, "location": "bedroom"}}}).json()


def run_child_door() -> dict:
    client.post("/api/reset", params={"preset_id": "child-door"})
    return client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "door_sensor", "target_person_id": "child_xiaoyu", "data": {"open": True, "visitor": "unknown", "location": "entrance"}}}).json()


def test_fall_creates_high_priority_feedback_goal_and_store_keeps_it():
    body = run_fall()
    goal = body["decision"]["care_goal"]
    assert goal["goal_type"] == "confirm_person_safety"
    assert goal["priority"] == "high"
    assert goal["requires_feedback"] is True
    assert goal["status"] == "awaiting_feedback"
    assert demo_store.active_goal() and demo_store.active_goal().goal_id == goal["goal_id"]
    assert demo_store.active_plan() and demo_store.active_plan().goal_id == goal["goal_id"]


def test_fall_plan_contains_required_high_level_steps_without_device_ids():
    plan = run_fall()["decision"]["agent_plan"]
    assert [step["intent"] for step in plan["steps"]] == ["improve_visibility", "reach_target", "observe_target", "request_response", "notify_guardian", "await_person_feedback"]
    assert "target_device_id" not in str(plan)
    assert all(step["status"] == "completed" for step in plan["steps"][:-1])
    assert plan["steps"][-1]["status"] == "awaiting_feedback"


def test_fall_plan_translation_preserves_phase4_device_actions():
    actions = run_fall()["decision"]["actions"]
    pairs = {(action["target_device_id"], action["capability"]) for action in actions}
    assert {("hallway_light_01", "switch"), ("bedroom_light_01", "switch"), ("robot_01", "navigate_to"), ("robot_01", "observe"), ("robot_01", "speak"), ("elder_watch_01", "vibrate"), ("guardian_phone_01", "push_notification")} <= pairs


def test_feedback_goal_memory_records_intervention_as_pending_not_complete():
    episode = run_fall()["context"]["people"]["elder_li"]["episodic_memory"][-1]
    assert "等待李爷爷反馈" in episode["result"]
    assert "完成" not in episode["result"] and "成功" not in episode["result"]


def test_child_door_creates_safety_goal():
    decision = run_child_door()["decision"]
    goal = decision["care_goal"]
    assert decision["risk_level"] == "high"
    assert goal["goal_type"] == "keep_child_safe_from_unknown_visitor"
    assert goal["target_person_id"] == "child_xiaoyu"
    assert goal["status"] == "awaiting_feedback"


def test_child_door_plan_contains_required_steps():
    steps = run_child_door()["decision"]["agent_plan"]["steps"]
    assert [step["intent"] for step in steps] == ["secure_entrance", "position_robot", "guide_child", "show_safety_message", "notify_guardian", "await_guardian_confirmation"]
    assert all(step["status"] == "completed" for step in steps[:-1])
    assert steps[-1]["status"] == "awaiting_feedback"


def test_child_door_plan_never_generates_unlock():
    actions = run_child_door()["decision"]["actions"]
    assert "unlock" not in {action["capability"] for action in actions}
    assert any(action["target_device_id"] == "door_lock_01" and action["capability"] == "lock" for action in actions)


def test_low_risk_companionship_needs_no_feedback_and_completes():
    client.post("/api/reset", params={"preset_id": "companion"})
    body = client.post("/api/events/trigger", json={"event": {"type": "conversation", "source": "user_voice", "target_person_id": "elder_li", "data": {"text": "今天有点无聊。", "location": "living_room"}}}).json()
    goal = body["decision"]["care_goal"]
    assert goal["goal_type"] == "provide_companionship"
    assert goal["requires_feedback"] is False
    assert goal["status"] == "completed"
    assert body["context"]["people"]["elder_li"]["episodic_memory"][-1]["result"] == body["decision"]["summary"]


def test_mock_mode_uses_deterministic_provider_without_api_call():
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.mock_mode is True
    assert isinstance(provider_for(settings), MockLLMProvider)


def test_all_eight_presets_continue_through_goal_and_plan():
    for preset_id, builder in PRESET_BUILDERS.items():
        client.post("/api/reset", params={"preset_id": preset_id})
        body = client.post("/api/events/trigger", json={"event": preset_event(preset_id).model_dump()}).json()
        assert body["decision"]["care_goal"]
        assert body["decision"]["agent_plan"]
        assert builder().schema_version == "2.0"


def test_three_static_histories_still_validate():
    for history_id in ["family_cold_start", "family_7d_normal", "family_30d_stable"]:
        context = history_context(history_id)
        assert context.active_history == history_id
        assert {person.role for person in context.people.values()} == {"elder", "child"}


def test_offline_fallback_is_generated_by_plan_and_skips_offline_watch():
    client.post("/api/reset", params={"preset_id": "device-offline"})
    body = client.post("/api/events/trigger", json={"event": {"type": "device", "source": "watch", "target_person_id": "elder_li", "data": {"online": False}}}).json()
    assert body["decision"]["care_goal"]["goal_type"] == "maintain_care_during_device_outage"
    device_ids = {action["target_device_id"] for action in body["decision"]["actions"]}
    assert {"robot_01", "guardian_phone_01", "smart_screen_01"} <= device_ids
    assert "elder_watch_01" not in device_ids
