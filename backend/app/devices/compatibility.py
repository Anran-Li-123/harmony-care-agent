from __future__ import annotations

from app.devices.registry import CapabilityMatcher
from app.schemas.models import ActionTarget, DeviceAction, DeviceType


LEGACY_CAPABILITY_MAP = {"move_to": "navigate_to", "camera_check": "observe", "health_check": "request_confirmation"}


def legacy_device_action_to_v2(action: DeviceAction, matcher: CapabilityMatcher, *, target_person_id: str | None = None) -> DeviceAction | None:
    """Central compatibility conversion from target/action to device/capability."""
    if action.target_device_id and action.capability:
        return action
    if not action.target or not action.action:
        return None
    capability = LEGACY_CAPABILITY_MAP.get(action.action, action.action)
    device_type = DeviceType(action.target.value)
    owner = target_person_id if action.target == ActionTarget.WATCH else "guardian" if action.target == ActionTarget.PHONE else None
    device = matcher.match(capability, target_person_id=owner, device_type=device_type)
    if not device:
        return None
    return DeviceAction(target_device_id=device.device_id, capability=capability, parameters=action.parameters, priority=action.priority, reason=action.reason or action.rationale, target=action.target, action=action.action, rationale=action.rationale or action.reason)
