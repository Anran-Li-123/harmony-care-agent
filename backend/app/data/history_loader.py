from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from app.schemas.models import ContextState


HISTORY_DIR = Path(__file__).with_name("history")
HISTORY_METADATA = [
    {"id": "family_cold_start", "label": "全新家庭", "description": "只有基础身份，尚未形成生活历史", "history_span": "首次启用"},
    {"id": "family_7d_normal", "label": "最近7天正常", "description": "一老一小最近一周的自然家庭生活", "history_span": "最近7天"},
    {"id": "family_30d_stable", "label": "30天稳定家庭", "description": "双方已形成有历史依据的稳定画像", "history_span": "最近30天"},
]


def _validate_history(context: ContextState, history_id: str) -> None:
    roles = [person.role for person in context.people.values()]
    if roles.count("elder") < 1 or roles.count("child") < 1:
        raise ValueError(f"{history_id} 必须同时包含至少一名老人和一名儿童")
    if context.active_history != history_id:
        raise ValueError(f"{history_id} 的 active_history 不一致")
    for person in context.people.values():
        timestamps = [episode.timestamp for episode in person.episodic_memory]
        if timestamps != sorted(timestamps):
            raise ValueError(f"{history_id}/{person.person_id} 的 Episode 未按时间排序")
        episode_ids = {episode.id for episode in person.episodic_memory}
        for profile in person.user_profile.values():
            if profile.source_type == "inferred" and (not profile.sources or not set(profile.sources).issubset(episode_ids)):
                raise ValueError(f"{history_id}/{person.person_id}/{profile.field} 缺少有效 Episode 依据")


@lru_cache(maxsize=8)
def _cached_history(history_id: str) -> ContextState:
    allowed = {item["id"] for item in HISTORY_METADATA}
    if history_id not in allowed:
        raise ValueError(f"未知家庭历史：{history_id}")
    payload = json.loads((HISTORY_DIR / f"{history_id}.json").read_text(encoding="utf-8"))
    context = ContextState.model_validate(payload)
    _validate_history(context, history_id)
    elder = next(person for person in context.people.values() if person.role == "elder")
    context.sync_legacy_projection(elder.person_id)
    return context


def history_context(history_id: str) -> ContextState:
    return deepcopy(_cached_history(history_id))


def history_options() -> list[dict[str, str | int]]:
    options: list[dict[str, str | int]] = []
    for metadata in HISTORY_METADATA:
        context = history_context(metadata["id"])
        options.append({
            **metadata,
            "episode_count": sum(len(person.episodic_memory) for person in context.people.values()),
        })
    return options
