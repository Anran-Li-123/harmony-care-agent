from __future__ import annotations

from abc import ABC, abstractmethod

from app.devices.compatibility import legacy_device_action_to_v2
from app.devices.registry import CapabilityMatcher, DeviceRegistry
from app.schemas.models import ActionIntent, ActionTarget, ContextState, DeviceAction, DeviceExecutionResult, DeviceType, HarmonyDevice


class DeviceAdapter(ABC):
    """Mock adapter contract; a future HarmonySoftBusAdapter can implement this boundary."""

    device_type: DeviceType

    @abstractmethod
    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult: ...

    @staticmethod
    def failure(device: HarmonyDevice, action: DeviceAction, message: str) -> DeviceExecutionResult:
        return DeviceExecutionResult(device_id=device.device_id, capability=action.capability or "unknown", success=False, message=message, resulting_state=dict(device.state))

    @staticmethod
    def success(device: HarmonyDevice, action: DeviceAction, message: str) -> DeviceExecutionResult:
        device.latest_action = action.capability or "unknown"
        device.state["latest_action"] = device.latest_action
        return DeviceExecutionResult(device_id=device.device_id, capability=action.capability or "unknown", success=True, message=message, resulting_state=dict(device.state))


class MockHarmonyAdapter(DeviceAdapter):
    def ensure_available(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult | None:
        if not device.online:
            return self.failure(device, action, f"{device.name}离线，能力未执行")
        if action.capability not in device.capabilities:
            return self.failure(device, action, f"{device.name}不支持 {action.capability}")
        return None


class HarmonySoftBusAdapter(DeviceAdapter):
    """Interface placeholder only; no real HarmonyOS SDK is connected in this Web demo."""

    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult:
        raise NotImplementedError("HarmonySoftBusAdapter 尚未接入真实 SDK")


class RobotAdapter(MockHarmonyAdapter):
    device_type = DeviceType.ROBOT

    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult:
        unavailable = self.ensure_available(device, action)
        if unavailable:
            return unavailable
        capability = action.capability
        if capability == "navigate_to":
            device.location = str(action.parameters.get("location", device.location))
            device.state["location"] = device.location
        elif capability == "speak":
            device.speech = str(action.parameters.get("text", ""))
            device.state["speech"] = device.speech
        elif capability == "observe":
            device.state["observing"] = str(action.parameters.get("location", device.location or "unknown"))
        elif capability == "follow":
            device.state["following"] = action.parameters.get("person_id")
        elif capability == "wait":
            device.state["mode"] = "waiting"
        elif capability == "play_audio":
            device.state["audio"] = action.parameters.get("content")
        device.status = "executing"
        device.state["status"] = device.status
        return self.success(device, action, f"{device.name} · {capability} 已执行")


class WatchAdapter(MockHarmonyAdapter):
    device_type = DeviceType.WATCH

    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult:
        unavailable = self.ensure_available(device, action)
        if unavailable:
            return unavailable
        message = str(action.parameters.get("message", "请确认当前状态"))
        device.latest_notification = message
        device.state["message"] = message
        device.status = "vibrating" if action.capability == "vibrate" else "awaiting_confirmation" if action.capability == "request_confirmation" else "displaying"
        device.state["status"] = device.status
        return self.success(device, action, f"{device.name} · {action.capability} 已执行")


class PhoneAdapter(MockHarmonyAdapter):
    device_type = DeviceType.PHONE

    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult:
        unavailable = self.ensure_available(device, action)
        if unavailable:
            return unavailable
        message = str(action.parameters.get("message", "家庭看护提醒"))
        device.latest_notification = message
        device.state["message"] = message
        device.status = "notified" if action.capability == "push_notification" else "awaiting_confirmation" if action.capability == "request_confirmation" else "displaying"
        device.state["status"] = device.status
        return self.success(device, action, f"{device.name} · {action.capability} 已执行")


class LightAdapter(MockHarmonyAdapter):
    device_type = DeviceType.LIGHT

    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult:
        unavailable = self.ensure_available(device, action)
        if unavailable:
            return unavailable
        if action.capability == "switch":
            value = str(action.parameters.get("value", "on")).lower()
            device.state["power"] = "on" if value in {"on", "true", "1"} else "off"
            device.state["brightness"] = 0 if device.state["power"] == "off" else int(device.state.get("brightness") or 100)
        elif action.capability == "set_brightness":
            brightness = max(0, min(100, int(action.parameters.get("value", 50))))
            device.state.update(power="on" if brightness else "off", brightness=brightness)
        device.status = "ready"
        device.state["status"] = device.status
        return self.success(device, action, f"{device.name}已{'开启' if device.state['power'] == 'on' else '关闭'}")


class DoorLockAdapter(MockHarmonyAdapter):
    device_type = DeviceType.DOOR_LOCK

    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult:
        unavailable = self.ensure_available(device, action)
        if unavailable:
            return unavailable
        if action.capability == "unlock":
            return self.failure(device, action, "Care Agent 禁止自动解锁")
        if action.capability == "lock":
            device.state["locked"] = True
        device.status = "ready"
        device.state["status"] = device.status
        message = f"{device.name}保持锁定" if action.capability == "lock" else f"{device.name}状态：{'已锁定' if device.state.get('locked') else '未锁定'}"
        return self.success(device, action, message)


class SmartScreenAdapter(MockHarmonyAdapter):
    device_type = DeviceType.SMART_SCREEN

    def execute(self, device: HarmonyDevice, action: DeviceAction) -> DeviceExecutionResult:
        unavailable = self.ensure_available(device, action)
        if unavailable:
            return unavailable
        if action.capability == "show_message":
            device.state.update(display="message", message=str(action.parameters.get("message", "家庭看护提醒")))
        elif action.capability == "display_status":
            device.state.update(display="status", message=str(action.parameters.get("status", "家庭状态正常")))
        elif action.capability == "start_call":
            device.state.update(display="call", call_active=True)
        device.status = "displaying"
        device.state["status"] = device.status
        return self.success(device, action, f"{device.name} · {action.capability} 已执行")


class ActionRouter:
    def __init__(self) -> None:
        self.adapters: dict[DeviceType, DeviceAdapter] = {
            DeviceType.ROBOT: RobotAdapter(), DeviceType.WATCH: WatchAdapter(), DeviceType.PHONE: PhoneAdapter(),
            DeviceType.LIGHT: LightAdapter(), DeviceType.DOOR_LOCK: DoorLockAdapter(), DeviceType.SMART_SCREEN: SmartScreenAdapter(),
        }

    def resolve(self, state: ContextState, intents: list[ActionIntent | DeviceAction]) -> list[DeviceAction]:
        matcher = CapabilityMatcher(DeviceRegistry(state.devices))
        resolved: list[DeviceAction] = []
        for intent in intents:
            if isinstance(intent, DeviceAction):
                action = legacy_device_action_to_v2(intent, matcher)
                if action:
                    resolved.append(action)
                continue
            device = matcher.match(intent.capability, location=intent.location, target_person_id=intent.target_person_id, device_type=intent.device_type, preferred_device_id=intent.target_device_id)
            if not device:
                continue
            legacy_target = ActionTarget(device.device_type.value) if device.device_type in {DeviceType.ROBOT, DeviceType.WATCH, DeviceType.PHONE} else None
            resolved.append(DeviceAction(target_device_id=device.device_id, capability=intent.capability, parameters=intent.parameters, priority=intent.priority, reason=intent.reason, target=legacy_target, action=intent.capability, rationale=intent.reason))
        return resolved

    def dispatch(self, state: ContextState, actions: list[DeviceAction]) -> list[DeviceExecutionResult]:
        registry = DeviceRegistry(state.devices)
        matcher = CapabilityMatcher(registry)
        results: list[DeviceExecutionResult] = []
        for original in actions:
            action = legacy_device_action_to_v2(original, matcher)
            if not action or not action.target_device_id:
                continue
            device = registry.get(action.target_device_id)
            if not device:
                results.append(DeviceExecutionResult(device_id=action.target_device_id, capability=action.capability or "unknown", success=False, message="设备未注册"))
                continue
            adapter = self.adapters.get(device.device_type)
            if adapter:
                results.append(adapter.execute(device, action))
        return results
