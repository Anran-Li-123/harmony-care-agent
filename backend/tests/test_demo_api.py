import os

# Tests stay deterministic and never consume a model call, even if local demo mode uses Qwen.
os.environ["MOCK_MODE"] = "true"

from fastapi.testclient import TestClient

from app.main import app


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
