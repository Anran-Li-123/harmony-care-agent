from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_ELDER_ID = "elder_li"
DEFAULT_CHILD_ID = "child_xiaoyu"


def legacy_person_id(value: str | None) -> str | None:
    """Map v1 person aliases to stable household person IDs."""
    if value in {None, "", "unknown", "household", "family", "environment"}:
        return None
    if value in {"child", "xiaoyu", DEFAULT_CHILD_ID}:
        return DEFAULT_CHILD_ID
    if value in {"grandpa", "elder", "li", DEFAULT_ELDER_ID}:
        return DEFAULT_ELDER_ID
    return value


def _legacy_context_owner(data: dict[str, Any]) -> str:
    preset = str(data.get("active_preset", ""))
    if preset.startswith("child-"):
        return DEFAULT_CHILD_ID
    environment = data.get("environment", {})
    occupancy = environment.get("occupancy", {}) if isinstance(environment, dict) else getattr(environment, "occupancy", {})
    occupants = {str(item) for values in occupancy.values() for item in values}
    if "child" in occupants and "grandpa" not in occupants:
        return DEFAULT_CHILD_ID
    profile = data.get("user_profile", {})
    preferred = profile.get("preferred_name", {})
    preferred_value = preferred.get("value") if isinstance(preferred, dict) else getattr(preferred, "value", None)
    if preferred_value in {"小安", "小宇"}:
        return DEFAULT_CHILD_ID
    return DEFAULT_ELDER_ID


def _location_for(occupancy: dict[str, list[str]], aliases: set[str]) -> str | None:
    for location, occupants in occupancy.items():
        if aliases.intersection(str(item) for item in occupants):
            return location
    return None


def _default_people(occupancy: dict[str, list[str]]) -> dict[str, dict[str, Any]]:
    return {
        DEFAULT_ELDER_ID: {
            "person_id": DEFAULT_ELDER_ID, "role": "elder", "name": "李爷爷",
            "location": _location_for(occupancy, {"grandpa", "elder", DEFAULT_ELDER_ID}), "status": "normal",
            "working_memory": [], "episodic_memory": [], "user_profile": {},
        },
        DEFAULT_CHILD_ID: {
            "person_id": DEFAULT_CHILD_ID, "role": "child", "name": "小宇",
            "location": _location_for(occupancy, {"child", DEFAULT_CHILD_ID}), "status": "normal",
            "working_memory": [], "episodic_memory": [], "user_profile": {},
        },
    }


def legacy_context_to_household(data: Any) -> Any:
    """Upgrade a v1 Context payload to v2 without discarding its legacy fields."""
    if not isinstance(data, dict):
        return data
    upgraded = deepcopy(data)
    environment = upgraded.get("environment", {})
    occupancy = environment.get("occupancy", {}) if isinstance(environment, dict) else getattr(environment, "occupancy", {})
    if upgraded.get("people"):
        defaults = _default_people(occupancy)
        roles = {person.get("role") if isinstance(person, dict) else getattr(person, "role", None) for person in upgraded["people"].values()}
        if "elder" not in roles:
            upgraded["people"][DEFAULT_ELDER_ID] = defaults[DEFAULT_ELDER_ID]
        if "child" not in roles:
            upgraded["people"][DEFAULT_CHILD_ID] = defaults[DEFAULT_CHILD_ID]
        upgraded["schema_version"] = "2.0"
        upgraded.setdefault("household", {"household_id": "family_001", "name": "示例家庭", "household_memory": []})
        upgraded.setdefault("active_history", None)
        return upgraded

    owner_id = _legacy_context_owner(upgraded)
    people = _default_people(occupancy)
    people[owner_id]["working_memory"] = deepcopy(upgraded.get("working_memory", []))
    people[owner_id]["episodic_memory"] = deepcopy(upgraded.get("episodic_memory", []))
    people[owner_id]["user_profile"] = deepcopy(upgraded.get("user_profile", {}))
    upgraded.update(
        schema_version="2.0",
        household={"household_id": "family_001", "name": "示例家庭", "household_memory": []},
        people=people,
        active_history=upgraded.get("active_history"),
    )
    return upgraded


def legacy_event_to_target(data: Any) -> Any:
    """Accept v1 CareEvent.person while making target_person_id canonical."""
    if not isinstance(data, dict):
        return data
    upgraded = deepcopy(data)
    if "target_person_id" not in upgraded:
        upgraded["target_person_id"] = legacy_person_id(upgraded.get("person"))
    return upgraded
