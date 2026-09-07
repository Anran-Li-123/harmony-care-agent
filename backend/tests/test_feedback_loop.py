import os

os.environ["MOCK_MODE"] = "true"

from fastapi.testclient import TestClient

from app.data.history_loader import history_context
from app.data.presets import PRESET_BUILDERS, preset_event
from app.main import app


client = TestClient(app)


def start_fall(*, phone_online: bool = True) -> dict:
    context = client.post("/api/demo/histories/family_30d_stable/load").json()
    if not phone_online:
        context["devices"]["phone"]["online"] = False
        context["devices"]["phone"]["status"] = "offline"
        client.post("/api/context", json=context)
    return client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "fall_detector", "target_person_id": "elder_li", "data": {"detected": True, "location": "bedroom"}}}).json()


def start_child_door() -> dict:
    client.post("/api/reset", params={"preset_id": "child-door"})
    return client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "door_sensor", "target_person_id": "child_xiaoyu", "data": {"open": True, "visitor": "unknown", "location": "entrance"}}}).json()


def feedback(goal_id: str, feedback_type: str, data: dict, *, source: str = "robot", target: str | None = None):
    return client.post(f"/api/goals/{goal_id}/feedback", json={"feedback_type": feedback_type, "source": source, "target_person_id": target, "data": data})


def test_feedback_without_active_goal_returns_clear_error():
    client.post("/api/reset", params={"preset_id": "companion"})
    response = feedback("goal_missing", "no_response", {"timeout": True})
    assert response.status_code == 409
    assert "没有可接收 Feedback" in response.json()["detail"]


def test_wrong_goal_id_is_rejected():
    start = start_fall()
    response = feedback("goal_wrong", "no_response", {"timeout": True})
    assert response.status_code == 409
    assert start["decision"]["care_goal"]["goal_id"] in response.json()["detail"]


def test_fall_im_fine_succeeds_downgrades_risk_and_resolves_memory():
    start = start_fall()
    goal_id = start["decision"]["care_goal"]["goal_id"]
    response = feedback(goal_id, "user_response", {"response": "im_fine"}, source="robot_microphone", target="elder_li")
    assert response.status_code == 200
    body = response.json()
    assert body["goal_evaluation"]["outcome"] == "SUCCESS"
    assert body["goal_evaluation"]["previous_risk_level"] == "high"
    assert body["goal_evaluation"]["updated_risk_level"] == "medium"
    assert body["updated_goal"]["status"] == "completed"
    assert body["updated_world_state"]["people"]["elder_li"]["responsive"] == "confirmed"
    episode = body["updated_context"]["people"]["elder_li"]["episodic_memory"][-1]
    assert episode["related_goal_id"] == goal_id and episode["status"] == "resolved"
    assert "正常交流" in episode["result"] and "医学" not in episode["result"]


def test_fall_cannot_stand_escalates_and_uses_high_priority_follow_up():
    start = start_fall()
    response = feedback(start["decision"]["care_goal"]["goal_id"], "user_response", {"response": "cannot_stand"}, source="robot_microphone", target="elder_li")
    body = response.json()
    assert body["goal_evaluation"]["outcome"] == "ESCALATE"
    assert body["updated_goal"]["status"] == "awaiting_feedback"
    assert any(action["capability"] == "push_notification" and action["priority"] == "critical" for action in body["actions"])
    assert body["updated_context"]["people"]["elder_li"]["episodic_memory"][-1]["status"] == "escalated"


def test_fall_no_response_escalates_with_robot_and_guardian_actions():
    start = start_fall()
    body = feedback(start["decision"]["care_goal"]["goal_id"], "no_response", {"timeout": True}).json()
    assert body["goal_evaluation"]["outcome"] == "ESCALATE"
    pairs = {(action["target_device_id"], action["capability"]) for action in body["actions"]}
    assert {("robot_01", "speak"), ("robot_01", "wait"), ("guardian_phone_01", "push_notification")} <= pairs
    assert "失去意识" not in str(body)


def test_watch_activity_only_continues_fall_goal():
    start = start_fall()
    body = feedback(start["decision"]["care_goal"]["goal_id"], "watch_activity", {"activity_detected": True}, source="elder_watch_01", target="elder_li").json()
    assert body["goal_evaluation"]["outcome"] == "CONTINUE"
    assert body["updated_goal"]["status"] == "awaiting_feedback"
    assert body["goal_evaluation"]["updated_risk_level"] == "medium"
    assert body["updated_world_state"]["people"]["elder_li"]["responsive"] == "unknown"


def test_guardian_confirmed_completes_goal_without_unlocking_door():
    start = start_child_door()
    body = feedback(start["decision"]["care_goal"]["goal_id"], "guardian_confirmation", {"decision": "confirmed"}, source="guardian_phone_01", target="child_xiaoyu").json()
    assert body["goal_evaluation"]["outcome"] == "SUCCESS"
    assert body["updated_goal"]["status"] == "completed"
    assert body["updated_context"]["devices"]["door_lock_01"]["state"]["locked"] is True
    assert "unlock" not in {action["capability"] for action in body["actions"]}


def test_guardian_rejected_completes_goal_and_keeps_door_locked():
    start = start_child_door()
    body = feedback(start["decision"]["care_goal"]["goal_id"], "guardian_confirmation", {"decision": "rejected"}, source="guardian_phone_01", target="child_xiaoyu").json()
    assert body["goal_evaluation"]["outcome"] == "SUCCESS"
    assert body["updated_context"]["devices"]["door_lock_01"]["state"]["locked"] is True
    assert "拒绝访客" in body["updated_context"]["people"]["child_xiaoyu"]["episodic_memory"][-1]["result"]


def test_guardian_no_response_continues_robot_and_door_protection():
    start = start_child_door()
    body = feedback(start["decision"]["care_goal"]["goal_id"], "guardian_no_response", {"timeout": True}, source="guardian_phone_01", target="child_xiaoyu").json()
    assert body["goal_evaluation"]["outcome"] == "CONTINUE"
    assert body["updated_goal"]["status"] == "awaiting_feedback"
    assert body["updated_context"]["devices"]["door_lock_01"]["state"]["locked"] is True
    assert {"lock", "speak", "show_message", "push_notification"} <= {action["capability"] for action in body["actions"]}


def test_feedback_updates_current_state_and_memory_not_profile():
    start = start_fall()
    profile_before = start["context"]["people"]["elder_li"]["user_profile"]
    body = feedback(start["decision"]["care_goal"]["goal_id"], "user_response", {"response": "im_fine"}, source="robot_microphone", target="elder_li").json()
    assert body["updated_context"]["people"]["elder_li"]["user_profile"] == profile_before
    assert body["updated_context"]["people"]["elder_li"]["status"] == "responsive"
    assert body["updated_context"]["people"]["elder_li"]["working_memory"][-1]["kind"] == "feedback"


def test_follow_up_plan_has_no_device_ids_and_actions_are_capability_matched():
    start = start_fall()
    body = feedback(start["decision"]["care_goal"]["goal_id"], "no_response", {"timeout": True}).json()
    assert "target_device_id" not in str(body["follow_up_plan"])
    assert all(action["target_device_id"] for action in body["actions"])
    assert all(result["device_id"] in {action["target_device_id"] for action in body["actions"]} for result in body["execution_results"])


def test_follow_up_still_executes_available_devices_when_phone_is_offline():
    start = start_fall(phone_online=False)
    assert start["decision"]["care_goal"]["status"] == "awaiting_feedback"
    body = feedback(start["decision"]["care_goal"]["goal_id"], "user_response", {"response": "cannot_stand"}, source="robot_microphone", target="elder_li").json()
    device_ids = {result["device_id"] for result in body["execution_results"] if result["success"]}
    assert {"robot_01", "smart_screen_01", "elder_watch_01"} <= device_ids
    assert "guardian_phone_01" not in {action["target_device_id"] for action in body["actions"]}
    assert body["updated_goal"]["status"] == "awaiting_feedback"


def test_completed_goal_rejects_additional_feedback():
    start = start_fall()
    goal_id = start["decision"]["care_goal"]["goal_id"]
    assert feedback(goal_id, "user_response", {"response": "im_fine"}, source="robot_microphone", target="elder_li").status_code == 200
    repeated = feedback(goal_id, "no_response", {"timeout": True})
    assert repeated.status_code == 409 and "已完成" in repeated.json()["detail"]


def test_reset_and_history_switch_clear_active_goal():
    first = start_fall()["decision"]["care_goal"]["goal_id"]
    client.post("/api/reset", params={"preset_id": "new-user"})
    assert feedback(first, "no_response", {"timeout": True}).status_code == 409
    second = start_fall()["decision"]["care_goal"]["goal_id"]
    client.post("/api/demo/histories/family_7d_normal/load")
    assert feedback(second, "no_response", {"timeout": True}).status_code == 409


def test_duplicate_feedback_is_rejected_while_goal_remains_active():
    start = start_fall()
    goal_id = start["decision"]["care_goal"]["goal_id"]
    assert feedback(goal_id, "no_response", {"timeout": True}).status_code == 200
    repeated = feedback(goal_id, "no_response", {"timeout": True})
    assert repeated.status_code == 409 and "重复 Feedback" in repeated.json()["detail"]


def test_feedback_target_mismatch_and_unsupported_type_are_clear_errors():
    start = start_fall()
    goal_id = start["decision"]["care_goal"]["goal_id"]
    mismatch = feedback(goal_id, "no_response", {"timeout": True}, target="child_xiaoyu")
    assert mismatch.status_code == 422 and "Target" in mismatch.json()["detail"]
    unsupported = feedback(goal_id, "free_text", {"text": "hello"})
    assert unsupported.status_code == 422 and "不支持的 Feedback Type" in str(unsupported.json())


def test_same_family_can_run_child_goal_after_fall_goal_completed():
    fall = start_fall()
    assert feedback(fall["decision"]["care_goal"]["goal_id"], "user_response", {"response": "im_fine"}, source="robot_microphone", target="elder_li").status_code == 200
    child = client.post("/api/events/trigger", json={"event": {"type": "sensor", "source": "door_sensor", "target_person_id": "child_xiaoyu", "data": {"open": True, "visitor": "unknown", "location": "entrance"}}})
    assert child.status_code == 200
    body = child.json()
    assert body["context"]["active_history"] == "family_30d_stable"
    assert body["decision"]["care_goal"]["goal_type"] == "keep_child_safe_from_unknown_visitor"


def test_old_presets_and_static_histories_continue_to_validate():
    for preset_id in PRESET_BUILDERS:
        client.post("/api/reset", params={"preset_id": preset_id})
        assert client.post("/api/events/trigger", json={"event": preset_event(preset_id).model_dump()}).status_code == 200
    for history_id in ["family_cold_start", "family_7d_normal", "family_30d_stable"]:
        assert history_context(history_id).active_history == history_id
