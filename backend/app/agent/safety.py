from app.schemas.models import CareEvent, ContextState, RiskLevel


class SafetyPolicy:
    """Deterministic guard rails precede LLM decisions for clear safety situations."""

    def evaluate(self, context: ContextState, event: CareEvent) -> tuple[RiskLevel | None, list[str]]:
        if event.source == "fall_detector" and event.data.get("detected"):
            evidence = ["跌倒感知器已触发", "安全事件必须优先现场确认"]
            if context.devices.get("robot", None) and context.devices["robot"].online:
                evidence.append("机器人在线，可立即前往现场")
            return RiskLevel.HIGH, evidence
        if event.source == "door_sensor" and event.data.get("open"):
            child_alone = "儿童独自在家" in context.environment.notes
            return (RiskLevel.HIGH if child_alone else RiskLevel.MEDIUM), ["门磁已打开", "需要确认门口情况"]
        if event.source == "watch_activity" and int(event.data.get("still_minutes", 0)) >= 30 and not event.data.get("acknowledged"):
            return RiskLevel.MEDIUM, ["手表记录到较长时间静止", "用户尚未确认状态", "该信号只用于请求确认，不作医疗诊断"]
        if event.source == "watch_geofence" and event.data.get("inside") is False:
            return RiskLevel.HIGH, ["儿童手表已离开家庭安全区", "需要由监护人确认当前位置"]
        if event.type == "device" and event.data.get("online") is False:
            return RiskLevel.MEDIUM, [f"{event.source} 已离线", "需要启用设备降级策略"]
        return None, []


HIGH_RISK_PROFILE_FIELDS = {"medical_condition", "allergy", "medication", "emergency_contact", "major_safety_risk", "family_relation"}

    
def profile_candidate_allowed(field: str, source_type: str, trusted: bool = False) -> bool:
    return field not in HIGH_RISK_PROFILE_FIELDS or source_type in {"explicit", "admin"} or trusted
