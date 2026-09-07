from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from app.config import Settings
from app.schemas.models import CareEvent, ContextState, WorldState


class LLMProvider(ABC):
    @abstractmethod
    def decide(self, context: ContextState, event: CareEvent, knowledge: list[str], world_state: WorldState | None = None) -> dict[str, Any]: ...

    @abstractmethod
    def sample_preset(self, prompt: str) -> str: ...

    @abstractmethod
    def sample_scenario(self, prompt: str) -> dict[str, str]: ...


class MockLLMProvider(LLMProvider):
    """A deliberately small deterministic provider for repeatable no-key demos."""

    def decide(self, context: ContextState, event: CareEvent, knowledge: list[str], world_state: WorldState | None = None) -> dict[str, Any]:
        text = str(event.data.get("text", ""))
        if "无聊" in text:
            preferred = context.user_profile.get("preferred_entertainment")
            entertainment = preferred.value if preferred else "轻松聊天"
            return {"risk_level": "low", "summary": f"识别到陪伴需求，建议提供{entertainment}和对话选择。", "evidence": ["用户主动表达无聊", "当前无安全传感器异常"]}
        if "李爷爷" in text or "叫我" in text:
            return {"risk_level": "low", "summary": "已记录首次自我介绍，并尊重用户指定的称呼。", "evidence": ["用户明确给出称呼偏好"]}
        if event.data.get("kind") == "sleep_pattern_review":
            return {"risk_level": "low", "summary": "近期多次晚间活动构成稳定证据，可审慎更新作息画像。", "evidence": ["近 3 条晚间活动事件", "并非由单次行为推断"]}
        return {"risk_level": "low", "summary": "已理解当前事件，系统将保持温和陪伴与持续观察。", "evidence": ["未触发确定性高风险规则"]}

    def sample_preset(self, prompt: str) -> str:
        text = prompt.lower()
        if any(term in text for term in ["安全区", "走远", "位置"]):
            return "child-safe-zone"
        if any(term in text for term in ["儿童", "门", "child"]):
            return "child-door"
        if any(term in text for term in ["静止", "未响应", "没动", "手表状态"]):
            return "elder-watch-inactive"
        if any(term in text for term in ["离线", "断开", "没电"]):
            return "device-offline"
        if any(term in text for term in ["夜间", "跌倒", "老人", "night", "fall"]):
            return "night-fall"
        if any(term in text for term in ["作息", "睡眠", "习惯"]):
            return "habit-change"
        return "companion"

    def sample_scenario(self, prompt: str) -> dict[str, str]:
        from app.data.scenarios import packs_for_preset

        return packs_for_preset(self.sample_preset(prompt))


class OpenAICompatibleProvider(LLMProvider):
    """DashScope/Qwen and other OpenAI-compatible backends share this provider."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("MOCK_MODE=false 时必须配置 OPENAI_API_KEY")
        self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url, timeout=settings.llm_timeout_seconds)
        self.model = settings.model_name

    def decide(self, context: ContextState, event: CareEvent, knowledge: list[str], world_state: WorldState | None = None) -> dict[str, Any]:
        target = world_state.people.get(event.target_person_id or "") if world_state else None
        relevant_room = world_state.rooms.get(target.location or "") if world_state and target else None
        compact_context = {
            "profile": {key: value.value for key, value in context.user_profile.items()},
            "devices": {key: {"online": value.online, "location": value.location} for key, value in context.devices.items()},
            "environment": context.environment.model_dump(),
            "recent_episodes": [item.model_dump() for item in context.episodic_memory[-4:]],
            "world_state": {
                "people": {key: value.model_dump() for key, value in world_state.people.items()},
                "robot": world_state.robot.model_dump() if world_state.robot else None,
                "relevant_room": relevant_room.model_dump() if relevant_room else None,
                "active_event": world_state.active_event.model_dump() if world_state.active_event else None,
                "risk_areas": [area.model_dump() for area in world_state.risk_areas],
            } if world_state else None,
        }
        prompt = {
            "role": "user",
            "content": "根据家庭看护上下文输出严格 JSON，不输出推理过程。字段仅包括 risk_level(low|medium|high), summary, evidence(string[]).不要诊断疾病或推断高风险长期信息。\n"
            + json.dumps({"context": compact_context, "event": event.model_dump(), "knowledge": knowledge}, ensure_ascii=False),
        }
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": "你是安全、温和的家庭看护决策助手。"}, prompt],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        if parsed.get("risk_level") not in {"low", "medium", "high"}:
            raise ValueError("LLM 输出缺少合法 risk_level")
        return parsed

    def sample_preset(self, prompt: str) -> str:
        """Use the real provider to select a safe template; templates keep its result schema-valid."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "将用户的家庭看护场景归类。只输出 JSON：{\"preset_id\": \"new-user|night-fall|elder-watch-inactive|child-door|child-safe-zone|companion|habit-change|device-offline\"}。"},
                {"role": "user", "content": prompt[:500]},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=40,
        )
        value = json.loads(response.choices[0].message.content or "{}").get("preset_id")
        if value not in {"new-user", "night-fall", "elder-watch-inactive", "child-door", "child-safe-zone", "companion", "habit-change", "device-offline"}:
            raise ValueError("LLM 返回了未知 Sample preset")
        return value

    def sample_scenario(self, prompt: str) -> dict[str, str]:
        allowed = {
            "persona_pack": {"elder", "child"},
            "memory_pack": {"blank", "recent", "routine", "stable", "changing"},
            "state_pack": {"daytime-normal", "elder-night", "child-home-alone", "wearable-alert", "device-degraded"},
            "trigger_pack": {"elder-intro", "elder-companion", "fall", "watch-inactive", "child-chat", "door-open", "safe-zone", "sleep-review", "device-offline"},
        }
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "你只负责从给定白名单中选择家庭看护演示数据包，不作医疗诊断。只输出 JSON，字段为 persona_pack、memory_pack、state_pack、trigger_pack。老人使用 elder，儿童使用 child。"},
                {"role": "user", "content": prompt[:500] + "\n白名单：" + json.dumps({key: sorted(value) for key, value in allowed.items()}, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=120,
        )
        value = json.loads(response.choices[0].message.content or "{}")
        for key, choices in allowed.items():
            if value.get(key) not in choices:
                raise ValueError(f"LLM 返回了未知 {key}")
        return {key: str(value[key]) for key in allowed}


def provider_for(settings: Settings) -> LLMProvider:
    return MockLLMProvider() if settings.mock_mode else OpenAICompatibleProvider(settings)
