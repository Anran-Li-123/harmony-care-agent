import os

# Tests stay deterministic and never consume a model call, even if local demo mode uses Qwen.
os.environ["MOCK_MODE"] = "true"

from fastapi.testclient import TestClient

from app.main import app
from app.data.history_loader import history_context
from app.schemas.models import ContextState


client = TestClient(app)


def test_presets_are_exposed():
    response = client.get("/api/demo/presets")
    assert response.status_code == 200
    assert len(response.json()) == 8


def test_scenario_options_and_structured_generation():
    options = client.get("/api/demo/scenario-options")
    assert options.status_code == 200
    assert {item["id"] for item in options.json()["personas"]} == {"elder", "child"}
    generated = client.post(
        "/api/scenarios/generate",
        json={"persona_pack": "child", "memory_pack": "stable", "state_pack": "child-home-alone", "trigger_pack": "door-open"},
    )
    assert generated.status_code == 200
    body = generated.json()
    assert body["schema_version"] == "1.0"
    assert body["event"]["source"] == "door_sensor"
    assert body["context"]["devices"]["watch"]["owner"] == "小安"


def test_incompatible_scenario_combination_is_rejected():
    response = client.post(
        "/api/scenarios/generate",
        json={"persona_pack": "child", "memory_pack": "changing", "state_pack": "daytime-normal", "trigger_pack": "child-chat"},
    )
    assert response.status_code == 422


def test_mock_ai_prompt_selects_schema_safe_scenario():
    response = client.post(
        "/api/scenarios/generate",
        json={"persona_pack": "elder", "memory_pack": "blank", "state_pack": "daytime-normal", "trigger_pack": "elder-intro", "prompt": "生成一个只有老人手表状态变化、没有对话的场景"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["event"]["source"] == "watch_activity"
    assert body["event"]["type"] == "sensor"


def test_night_fall_routes_actions_and_memory():
    assert client.post("/api/reset?preset_id=night-fall").status_code == 200
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "sensor", "source": "fall_detector", "person": "grandpa", "data": {"detected": True, "location": "bedroom"}}},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["decision"]["risk_level"] == "high"
    assert {action["target"] for action in body["decision"]["actions"]} == {"robot", "watch", "phone"}
    assert body["context"]["devices"]["robot"]["location"] == "bedroom"
    assert len(body["context"]["episodic_memory"]) == 2
    assert body["context"]["devices"]["watch"]["latest_notification"] == "检测到异常，请确认您的状态"


def test_cold_start_learns_only_explicit_name():
    client.post("/api/reset?preset_id=new-user")
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "conversation", "source": "user_voice", "person": "grandpa", "data": {"text": "我叫李建国，你叫我李爷爷就行。"}}},
    )
    assert result.status_code == 200
    assert result.json()["context"]["user_profile"]["preferred_name"]["value"] == "李爷爷"


def test_habit_changes_after_multiple_evidence_records():
    client.post("/api/reset?preset_id=habit-change")
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "manual", "source": "profile_observer", "person": "grandpa", "data": {"kind": "sleep_pattern_review", "evidence_count": 3}}},
    )
    assert result.status_code == 200
    assert result.json()["context"]["user_profile"]["sleep_time"]["value"] == "22:45"


def test_elder_watch_inactivity_requests_confirmation_without_diagnosis():
    client.post("/api/reset?preset_id=elder-watch-inactive")
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "sensor", "source": "watch_activity", "person": "grandpa", "data": {"still_minutes": 45, "acknowledged": False, "location": "bedroom"}}},
    )
    assert result.status_code == 200
    decision = result.json()["decision"]
    assert decision["risk_level"] == "medium"
    assert {action["target"] for action in decision["actions"]} == {"robot", "watch", "phone"}
    assert "诊断" not in decision["summary"]


def test_child_safe_zone_routes_watch_and_phone():
    client.post("/api/reset?preset_id=child-safe-zone")
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "sensor", "source": "watch_geofence", "person": "child", "data": {"inside": False, "zone": "家庭安全区"}}},
    )
    assert result.status_code == 200
    decision = result.json()["decision"]
    assert decision["risk_level"] == "high"
    assert {action["target"] for action in decision["actions"]} == {"robot", "watch", "phone"}


def test_device_offline_uses_available_terminals():
    client.post("/api/reset?preset_id=device-offline")
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "device", "source": "watch", "person": "grandpa", "data": {"online": False}}},
    )
    assert result.status_code == 200
    body = result.json()
    assert body["decision"]["risk_level"] == "medium"
    assert {action["target"] for action in body["decision"]["actions"]} == {"robot", "phone"}
    assert body["context"]["devices"]["watch"]["online"] is False


def test_versioned_scenario_upload(tmp_path):
    scenario = client.get("/api/demo/scenarios/new-user").json()
    response = client.post(
        "/api/context/upload",
        files={"file": ("scenario.json", __import__("json").dumps(scenario, ensure_ascii=False).encode("utf-8"), "application/json")},
    )
    assert response.status_code == 200
    assert response.json()["scenario"]["source"] == "upload"
    assert response.json()["event"]["type"] == "conversation"


def test_v2_context_contains_elder_and_child():
    context = client.post("/api/reset?preset_id=new-user").json()
    assert context["schema_version"] == "2.0"
    assert {person["role"] for person in context["people"].values()} >= {"elder", "child"}
    assert context["people"]["elder_li"]["name"] == "李爷爷"
    assert context["people"]["child_xiaoyu"]["name"] == "小宇"


def test_v1_context_is_upgraded_by_central_compatibility_layer():
    legacy = {
        "working_memory": [],
        "episodic_memory": [],
        "user_profile": {"preferred_name": {"field": "preferred_name", "value": "小安", "confidence": 1, "source_type": "explicit", "sources": ["family_setup"]}},
        "knowledge_base": [],
        "devices": {},
        "sensors": {},
        "environment": {"occupancy": {"living_room": ["child"]}},
        "active_preset": "child-door",
    }
    context = ContextState.model_validate(legacy)
    assert context.schema_version == "2.0"
    assert context.people["child_xiaoyu"].user_profile["preferred_name"].value == "小安"
    assert context.people["elder_li"].role == "elder"


def test_elder_event_only_updates_elder_memory():
    before = client.post("/api/reset?preset_id=new-user").json()
    child_before = before["people"]["child_xiaoyu"]
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "conversation", "source": "user_voice", "target_person_id": "elder_li", "data": {"text": "今天想聊聊天。"}}},
    ).json()["context"]
    assert len(result["people"]["elder_li"]["working_memory"]) == 1
    assert result["people"]["child_xiaoyu"]["working_memory"] == child_before["working_memory"]
    assert result["people"]["child_xiaoyu"]["episodic_memory"] == child_before["episodic_memory"]


def test_child_event_only_updates_child_memory():
    before = client.post("/api/reset?preset_id=child-door").json()
    elder_before = before["people"]["elder_li"]
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "conversation", "source": "user_voice", "target_person_id": "child_xiaoyu", "data": {"text": "我已经到家了。"}}},
    ).json()["context"]
    assert len(result["people"]["child_xiaoyu"]["working_memory"]) == 1
    assert result["people"]["elder_li"]["working_memory"] == elder_before["working_memory"]
    assert result["people"]["elder_li"]["episodic_memory"] == elder_before["episodic_memory"]


def test_household_event_does_not_modify_any_person_profile():
    before = client.post("/api/reset?preset_id=companion").json()
    profiles_before = {key: value["user_profile"] for key, value in before["people"].items()}
    result = client.post(
        "/api/events/trigger",
        json={"event": {"type": "environment", "source": "smoke_detector", "target_person_id": None, "data": {"status": "normal"}}},
    ).json()["context"]
    assert {key: value["user_profile"] for key, value in result["people"].items()} == profiles_before
    assert len(result["household"]["household_memory"]) == 1


def test_all_legacy_presets_still_load_and_run():
    for preset_id in ["new-user", "night-fall", "elder-watch-inactive", "child-door", "child-safe-zone", "companion", "habit-change", "device-offline"]:
        scenario = client.get(f"/api/demo/scenarios/{preset_id}")
        assert scenario.status_code == 200
        payload = scenario.json()
        assert payload["context"]["schema_version"] == "2.0"
        assert {person["role"] for person in payload["context"]["people"].values()} >= {"elder", "child"}
        result = client.post("/api/events/trigger", json={"event": payload["event"]})
        assert result.status_code == 200


def test_static_household_histories_have_expected_scale_and_people():
    expected_counts = {"family_cold_start": 0, "family_7d_normal": 30, "family_30d_stable": 52}
    response = client.get("/api/demo/histories")
    assert response.status_code == 200
    assert {item["id"]: item["episode_count"] for item in response.json()} == expected_counts
    for history_id, count in expected_counts.items():
        context = history_context(history_id)
        assert sum(len(person.episodic_memory) for person in context.people.values()) == count
        assert {person.role for person in context.people.values()} >= {"elder", "child"}


def test_static_history_profiles_only_reference_existing_episodes():
    for history_id in ["family_7d_normal", "family_30d_stable"]:
        context = history_context(history_id)
        for person in context.people.values():
            episode_ids = {episode.id for episode in person.episodic_memory}
            for profile in person.user_profile.values():
                if profile.source_type == "inferred":
                    assert profile.sources
                    assert set(profile.sources) <= episode_ids


def test_loading_history_does_not_run_an_event_and_keeps_event_switchable():
    loaded = client.post("/api/demo/histories/family_30d_stable/load")
    assert loaded.status_code == 200
    before = loaded.json()
    assert before["active_history"] == "family_30d_stable"
    assert before["devices"]["robot"]["latest_action"] == "自动回充完成"
    elder_result = client.post("/api/events/trigger", json={"event": {"type": "conversation", "source": "user_voice", "target_person_id": "elder_li", "data": {"text": "今天有点无聊。"}}})
    assert elder_result.status_code == 200
    child_before = elder_result.json()["context"]["people"]["child_xiaoyu"]["episodic_memory"]
    child_result = client.post("/api/events/trigger", json={"event": {"type": "conversation", "source": "user_voice", "target_person_id": "child_xiaoyu", "data": {"text": "陪我聊一会儿。"}}})
    assert child_result.status_code == 200
    assert child_result.json()["context"]["active_history"] == "family_30d_stable"
    assert len(child_result.json()["context"]["people"]["child_xiaoyu"]["episodic_memory"]) == len(child_before) + 1
