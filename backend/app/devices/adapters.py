from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.models import ContextState, DeviceAction


class DeviceAdapter(ABC):
    """Replace these adapters with HarmonyOS implementations without changing Agent logic."""

    target: str

    @abstractmethod
    def execute(self, state: ContextState, action: DeviceAction) -> str: ...


class RobotAdapter(DeviceAdapter):
    target = "robot"

    def execute(self, state: ContextState, action: DeviceAction) -> str:
        robot = state.devices.get("robot")
        if not robot or not robot.online:
            return "机器人离线，动作已降级记录"
        if action.action == "move_to":
            robot.location = str(action.parameters.get("location", robot.location))
        if action.action == "speak":
            robot.speech = str(action.parameters.get("text", ""))
        robot.latest_action = action.action
        robot.status = "executing"
        return f"Robot · {action.action} 已执行"


class WatchAdapter(DeviceAdapter):
    target = "watch"

    def execute(self, state: ContextState, action: DeviceAction) -> str:
        watch = state.devices.get("watch")
        if not watch or not watch.online:
            return "手表离线，已转由手机提醒"
        watch.latest_action = action.action
        if "message" in action.parameters:
            watch.latest_notification = str(action.parameters["message"])
        elif not watch.latest_notification:
            watch.latest_notification = "请确认当前状态"
        watch.status = "vibrating" if action.action == "vibrate" else "executing"
        return f"Watch · {action.action} 已执行"


class PhoneAdapter(DeviceAdapter):
    target = "phone"

    def execute(self, state: ContextState, action: DeviceAction) -> str:
        phone = state.devices.get("phone")
        if not phone or not phone.online:
            return "手机离线，动作已进入待重试队列"
        phone.latest_action = action.action
        phone.latest_notification = str(action.parameters.get("message", "家庭看护提醒"))
        phone.status = "notified"
        return f"Phone · {action.action} 已执行"


class ActionRouter:
    def __init__(self) -> None:
        self.adapters = {"robot": RobotAdapter(), "watch": WatchAdapter(), "phone": PhoneAdapter()}

    def dispatch(self, state: ContextState, actions: list[DeviceAction]) -> list[str]:
        results: list[str] = []
        for action in actions:
            adapter = self.adapters.get(action.target.value)
            if adapter:
                results.append(adapter.execute(state, action))
        return results
