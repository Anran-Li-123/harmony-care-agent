from __future__ import annotations

from app.schemas.compatibility import DEFAULT_CHILD_ID, DEFAULT_ELDER_ID
from app.schemas.models import (
    ActiveWorldEvent,
    CareEvent,
    ContextState,
    DeviceWorldState,
    PersonWorldState,
    RiskArea,
    RobotWorldState,
    RoomWorldState,
    SensorWorldState,
    WorldState,
    now_iso,
)


HOME_ROOMS = ("bedroom", "living_room", "entrance", "kitchen")


class WorldModelBuilder:
    """Deterministically derives a semantic current-world snapshot from Context + Event."""

    def build(self, context: ContextState, event: CareEvent | None = None) -> WorldState:
        people = {
            person_id: PersonWorldState(
                person_id=person.person_id,
                role=person.role,
                name=person.name,
                location=self._person_location(context, person_id, person.location),
                status=person.status,
                responsive=person.responsive,
            )
            for person_id, person in context.people.items()
        }
        robot_device = context.devices.get("robot")
        robot = RobotWorldState(
            device_id=robot_device.id,
            location=robot_device.location,
            online=robot_device.online,
            status=robot_device.status,
        ) if robot_device else None
        devices = {
            key: DeviceWorldState(
                device_id=device.id,
                device_type=device.kind.value,
                name=device.name,
                location=device.location,
                online=device.online,
                status=device.status,
                state=dict(device.state),
            )
            for key, device in context.devices.items()
            if key != "robot"
        }
        sensors = {
            key: SensorWorldState(
                sensor_id=sensor.id,
                label=sensor.label,
                location=sensor.location,
                status=sensor.status,
                value=sensor.value,
            )
            for key, sensor in context.sensors.items()
        }
        rooms = self._rooms(context, people)
        world = WorldState(
            timestamp=event.timestamp if event else now_iso(),
            people=people,
            robot=robot,
            rooms=rooms,
            devices=devices,
            sensors=sensors,
            environment=context.environment.model_copy(deep=True),
            active_event=ActiveWorldEvent(
                event_id=event.id,
                target_person_id=event.target_person_id,
                type=event.type,
                source=event.source,
                timestamp=event.timestamp,
            ) if event else None,
        )
        if event:
            self._apply_event(world, context, event)
        return world

    @staticmethod
    def _person_location(context: ContextState, person_id: str, fallback: str | None) -> str | None:
        aliases = {person_id}
        if person_id == DEFAULT_ELDER_ID:
            aliases.update({"grandpa", "elder"})
        if person_id == DEFAULT_CHILD_ID:
            aliases.add("child")
        for location, occupants in context.environment.occupancy.items():
            if aliases.intersection(occupants):
                return location
        return fallback

    @staticmethod
    def _rooms(context: ContextState, people: dict[str, PersonWorldState]) -> dict[str, RoomWorldState]:
        room_ids = set(HOME_ROOMS) | set(context.environment.occupancy)
        room_ids.update(person.location for person in people.values() if person.location in HOME_ROOMS)
        rooms = {
            room_id: RoomWorldState(
                room_id=room_id,
                occupied_by=[person.person_id for person in people.values() if person.location == room_id],
                lighting=context.environment.lighting,
            )
            for room_id in sorted(room_ids)
        }
        return rooms

    def _apply_event(self, world: WorldState, context: ContextState, event: CareEvent) -> None:
        target = world.people.get(event.target_person_id or "")
        location = str(event.data.get("location") or (target.location if target else "unknown"))
        if target and location != "unknown":
            self._move_person(world, target.person_id, location)
        sensor = world.sensors.get(event.source)
        if sensor and event.type in {"sensor", "environment"}:
            sensor.status = "triggered"
            sensor.value = event.data

        if event.source == "fall_detector" and event.data.get("detected") and target:
            target.status = "suspected_fall"
            target.responsive = "unknown"
            self._add_risk(world, location, "fall_detector_triggered", "high")
        elif event.source == "watch_activity" and int(event.data.get("still_minutes", 0)) >= 30 and target:
            target.status = "needs_confirmation"
            target.responsive = "unknown"
            self._add_risk(world, location, "watch_inactivity_needs_confirmation", "concern")
        elif event.source == "door_sensor" and target and target.role == "child":
            target.status = "safety_concern"
            child_at_home = target.location in HOME_ROOMS
            guardian_absent = any(note in context.environment.notes for note in {"家长外出", "儿童独自在家"})
            reason = "child_alone_door_event" if child_at_home and guardian_absent else "child_door_event"
            self._add_risk(world, "entrance", reason, "concern")
        elif event.source == "watch_geofence" and event.data.get("inside") is False and target:
            target.status = "outside_safe_zone"
            self._add_risk(world, str(event.data.get("last_seen", "outside_safe_zone")), "safe_zone_exit", "concern")

        if event.type == "device" and event.data.get("online") is False:
            if world.robot and event.source in {"robot", world.robot.device_id}:
                world.robot.online = False
                world.robot.status = "offline"
            for key, device in world.devices.items():
                if event.source in {key, device.device_id}:
                    device.online = False
                    device.status = "offline"

    @staticmethod
    def _move_person(world: WorldState, person_id: str, location: str) -> None:
        person = world.people[person_id]
        person.location = location
        for room in world.rooms.values():
            if person_id in room.occupied_by:
                room.occupied_by.remove(person_id)
        if location in world.rooms and person_id not in world.rooms[location].occupied_by:
            world.rooms[location].occupied_by.append(person_id)

    @staticmethod
    def _add_risk(world: WorldState, location: str, reason: str, indicator: str) -> None:
        risk_indicator = "high" if indicator == "high" else "concern"
        world.risk_areas.append(RiskArea(location=location, reason=reason, risk_indicator=risk_indicator))
        if location in world.rooms:
            world.rooms[location].risk_indicator = risk_indicator
