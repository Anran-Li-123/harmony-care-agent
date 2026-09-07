from __future__ import annotations

import re

from app.agent.safety import profile_candidate_allowed
from app.schemas.models import (
    AgentDecision,
    CareEvent,
    ContextState,
    Episode,
    MemoryCandidate,
    ProfileCandidate,
    ProfileChange,
    ProfileEntry,
    WorkingMemoryItem,
)


class MemoryExtractor:
    def extract(self, context: ContextState, event: CareEvent, decision: AgentDecision) -> list[MemoryCandidate]:
        candidates = [MemoryCandidate(type="working", reason="保留当前事件供本会话后续决策使用", preview=self._summary(event))]
        if event.type in {"sensor", "conversation", "manual"}:
            candidates.append(MemoryCandidate(type="episodic", reason="可追溯的重要交互/状态变化", preview=self._summary(event)))
        return candidates

    def apply(self, context: ContextState, event: CareEvent, decision: AgentDecision) -> str:
        summary = self._summary(event)
        person = context.target_person(event.target_person_id)
        if person is None:
            context.household.household_memory.append(WorkingMemoryItem(kind=event.type, content=summary, expires_hint="家庭事件"))
            context.household.household_memory = context.household.household_memory[-12:]
            context.sync_legacy_projection(None)
            return ""
        person.working_memory.append(WorkingMemoryItem(kind=event.type, content=summary))
        person.working_memory = person.working_memory[-6:]
        if any(item.type == "episodic" for item in decision.memory_updates):
            person.episodic_memory.append(
                Episode(person=person.person_id, event=summary, location=str(event.data.get("location", "unknown")), actions=[a.capability or a.action or "unknown" for a in decision.actions], result=decision.summary, importance="high" if decision.risk_level.value == "high" else "normal")
            )
        context.sync_legacy_projection(person.person_id)
        return person.episodic_memory[-1].id if person.episodic_memory else ""

    @staticmethod
    def _summary(event: CareEvent) -> str:
        if event.type == "conversation":
            return str(event.data.get("text", "用户发起对话"))
        if event.source == "fall_detector":
            return "卧室疑似跌倒感知触发"
        if event.source == "door_sensor":
            return "入口门磁打开"
        if event.source == "watch_activity":
            return f"手表记录到连续 {event.data.get('still_minutes', 0)} 分钟静止且尚未确认"
        if event.source == "watch_geofence":
            return "儿童手表离开家庭安全区"
        if event.type == "device" and event.data.get("online") is False:
            return f"{event.source} 连接中断"
        if event.data.get("kind") == "sleep_pattern_review":
            return "系统汇总近期晚间活动记录"
        return f"{event.source} 状态变化"


class ProfileUpdater:
    def candidates(self, context: ContextState, event: CareEvent, episode_id: str) -> list[ProfileCandidate]:
        person = context.target_person(event.target_person_id)
        if person is None:
            return []
        text = str(event.data.get("text", ""))
        candidates: list[ProfileCandidate] = []
        explicit_name = event.data.get("preferred_name")
        if not explicit_name and "叫我" in text:
            match = re.search(r"叫我([\u4e00-\u9fffA-Za-z0-9·]{1,8}?)(?:就|吧|。|，|,|$)", text)
            explicit_name = match.group(1) if match else None
        if explicit_name:
            candidates.append(ProfileCandidate(field="preferred_name", value=str(explicit_name), confidence=1.0, source_type="explicit", sources=[episode_id], rationale="用户明确指定称呼"))
        if event.data.get("kind") == "sleep_pattern_review" and len([e for e in person.episodic_memory if "22:" in e.event or "23:" in e.event]) >= 3:
            candidates.append(ProfileCandidate(field="sleep_time", value="22:45", confidence=0.84, source_type="inferred", sources=["episode_late_1", "episode_late_2", "episode_late_3"], rationale="连续多个晚间活动事件支持作息已发生变化"))
        return [candidate for candidate in candidates if profile_candidate_allowed(candidate.field, candidate.source_type)]

    def apply(self, context: ContextState, candidates: list[ProfileCandidate], target_person_id: str | None) -> list[ProfileChange]:
        person = context.target_person(target_person_id)
        if person is None:
            return []
        changes: list[ProfileChange] = []
        for candidate in candidates:
            prior = person.user_profile.get(candidate.field)
            before = prior.value if prior else None
            if prior and prior.source_type == "explicit" and candidate.source_type == "inferred":
                continue
            person.user_profile[candidate.field] = ProfileEntry(field=candidate.field, value=candidate.value, confidence=candidate.confidence, source_type=candidate.source_type, sources=candidate.sources)
            message = "建立新的长期画像" if before is None else "检测到用户生活习惯变化"
            changes.append(ProfileChange(field=candidate.field, before=before, after=candidate.value, confidence=candidate.confidence, explanation=message))
        context.sync_legacy_projection(person.person_id)
        return changes
