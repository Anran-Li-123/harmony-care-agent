from __future__ import annotations

from app.schemas.models import DeviceType, HarmonyDevice


class DeviceRegistry:
    """Read/query facade over the current Context device objects."""

    def __init__(self, devices: dict[str, HarmonyDevice]) -> None:
        self._devices = devices

    def all(self) -> list[HarmonyDevice]:
        return list(self._devices.values())

    def get(self, device_id: str) -> HarmonyDevice | None:
        direct = self._devices.get(device_id)
        if direct:
            return direct
        return next((device for device in self._devices.values() if device.device_id == device_id), None)

    def by_type(self, device_type: DeviceType | str) -> list[HarmonyDevice]:
        value = DeviceType(device_type)
        return [device for device in self._devices.values() if device.device_type == value]

    def by_location(self, location: str) -> list[HarmonyDevice]:
        return [device for device in self._devices.values() if device.location == location]

    def by_capability(self, capability: str, online_only: bool = False) -> list[HarmonyDevice]:
        return [device for device in self._devices.values() if capability in device.capabilities and (device.online or not online_only)]

    def is_online(self, device_id: str) -> bool:
        device = self.get(device_id)
        return bool(device and device.online)

    def state(self, device_id: str) -> dict[str, object] | None:
        device = self.get(device_id)
        return dict(device.state) if device else None

    def for_event_source(self, source: str, target_person_id: str | None = None) -> HarmonyDevice | None:
        direct = self.get(source)
        if direct:
            return direct
        type_aliases = {"robot": DeviceType.ROBOT, "watch": DeviceType.WATCH, "phone": DeviceType.PHONE}
        device_type = type_aliases.get(source)
        if not device_type:
            return None
        candidates = self.by_type(device_type)
        if target_person_id:
            owned = [device for device in candidates if device.owner_person_id == target_person_id]
            if owned:
                candidates = owned
        return sorted(candidates, key=lambda device: device.device_id)[0] if candidates else None


class CapabilityMatcher:
    """Deterministic capability lookup by device, person and semantic location."""

    def __init__(self, registry: DeviceRegistry) -> None:
        self.registry = registry

    def match(
        self,
        capability: str,
        *,
        location: str | None = None,
        target_person_id: str | None = None,
        device_type: DeviceType | str | None = None,
        preferred_device_id: str | None = None,
        include_offline: bool = False,
    ) -> HarmonyDevice | None:
        candidates = self.registry.by_capability(capability, online_only=not include_offline)
        if preferred_device_id:
            preferred = self.registry.get(preferred_device_id)
            if preferred in candidates:
                return preferred
        if device_type is not None:
            typed = [device for device in candidates if device.device_type == DeviceType(device_type)]
            if not typed:
                return None
            candidates = typed
        if target_person_id:
            owned = [device for device in candidates if device.owner_person_id == target_person_id]
            if owned:
                candidates = owned
            elif any(device.owner_person_id for device in candidates):
                return None
        if location:
            local = [device for device in candidates if device.location == location]
            if local:
                candidates = local
            elif any(device.location for device in candidates):
                return None
        return sorted(candidates, key=lambda device: device.device_id)[0] if candidates else None
