from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import ValidationError

from app.agent.orchestrator import AgentOrchestrator
from app.agent.feedback import FeedbackCoordinator
from app.devices.registry import DeviceRegistry
from app.config import get_settings
from app.data.presets import PRESET_METADATA, preset_context
from app.data.history_loader import history_context, history_options
from app.data.scenarios import compose_scenario, draft_from_preset, options_payload
from app.schemas.models import (
    ContextState,
    CareGoalStatus,
    FeedbackEvent,
    FeedbackResponse,
    FeedbackSubmission,
    GenerateRequest,
    ScenarioDraft,
    ScenarioGenerationRequest,
    ScenarioOptions,
    TriggerRequest,
    TriggerResponse,
    UploadResponse,
)
from app.services.store import demo_store
from app.agent.llm import provider_for

router = APIRouter(prefix="/api")


def current_orchestrator() -> AgentOrchestrator:
    settings = get_settings()
    return AgentOrchestrator(provider_for(settings), "mock" if settings.mock_mode else "openai-compatible")


@router.get("/health")
def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {"status": "ok", "mock_mode": settings.mock_mode, "model": settings.model_name}


@router.get("/demo/presets")
def presets() -> list[dict[str, str]]:
    return PRESET_METADATA


@router.get("/demo/histories")
def histories() -> list[dict[str, str | int]]:
    return history_options()


@router.get("/demo/histories/{history_id}", response_model=ContextState)
def get_history(history_id: str) -> ContextState:
    try:
        return history_context(history_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/demo/histories/{history_id}/load", response_model=ContextState)
def load_history(history_id: str) -> ContextState:
    try:
        return demo_store.replace_context(history_context(history_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/demo/scenario-options", response_model=ScenarioOptions)
def scenario_options() -> ScenarioOptions:
    return options_payload()


@router.get("/demo/scenarios/{preset_id}", response_model=ScenarioDraft)
def demo_scenario(preset_id: str) -> ScenarioDraft:
    try:
        draft = draft_from_preset(preset_id)
    except (ValueError, StopIteration) as exc:
        raise HTTPException(status_code=404, detail=f"未知演示场景：{preset_id}") from exc
    draft.context = demo_store.replace_context(draft.context)
    return draft


@router.get("/context", response_model=ContextState)
def get_context() -> ContextState:
    return demo_store.context()


@router.post("/context", response_model=ContextState)
def set_context(context: ContextState) -> ContextState:
    return demo_store.replace_context(context)


@router.post("/context/generate", response_model=ContextState)
def generate_context(request: GenerateRequest) -> ContextState:
    """Mock mode selects a local template; Real mode uses LLM classification then a schema-safe template."""
    try:
        preset_id = provider_for(get_settings()).sample_preset(request.prompt)
    except Exception:
        # The Demo remains usable when a real LLM times out or returns malformed JSON.
        preset_id = "companion"
    context = preset_context(preset_id)
    context.environment.notes.append(f"AI Sample：{request.prompt[:80]}")
    return demo_store.replace_context(context)


@router.post("/scenarios/generate", response_model=ScenarioDraft)
def generate_scenario(request: ScenarioGenerationRequest) -> ScenarioDraft:
    settings = get_settings()
    source = "template"
    warnings: list[str] = []
    selected = request
    if request.prompt and request.prompt.strip():
        try:
            packs = provider_for(settings).sample_scenario(request.prompt.strip())
            selected = ScenarioGenerationRequest(**packs, prompt=request.prompt)
            source = "template" if settings.mock_mode else "ai"
        except Exception:
            source = "fallback"
            warnings.append("AI 场景构造暂不可用，已按当前选择生成稳定模板。")
    try:
        draft = compose_scenario(selected, source=source, warnings=warnings)
    except ValueError as exc:
        if selected is not request:
            try:
                warnings.append("AI 返回的数据包组合不兼容，已回退到当前结构化选择。")
                draft = compose_scenario(request, source="fallback", warnings=warnings)
            except ValueError as fallback_exc:
                raise HTTPException(status_code=422, detail=str(fallback_exc)) from fallback_exc
        else:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if request.prompt:
        draft.context.environment.notes.append(f"场景描述：{request.prompt[:80]}")
    draft.context = demo_store.replace_context(draft.context)
    return draft


@router.post("/context/upload", response_model=UploadResponse)
async def upload_context(file: UploadFile = File(...)) -> UploadResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".json", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="仅支持 .json、.txt、.md 文件")
    payload = await file.read()
    if len(payload) > 1_000_000:
        raise HTTPException(status_code=400, detail="文件不能超过 1 MB")
    try:
        content = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="文件必须是 UTF-8 编码") from exc
    if suffix == ".json":
        try:
            value = json.loads(content)
            if isinstance(value, dict) and value.get("schema_version") and "context" in value and "event" in value:
                scenario = ScenarioDraft.model_validate(value)
                scenario.source = "upload"
                scenario.context = demo_store.replace_context(scenario.context)
                return UploadResponse(context=scenario.context, event=scenario.event, scenario=scenario, message="完整场景 JSON 已导入，可直接运行动画")
            context = ContextState.model_validate(value)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise HTTPException(status_code=422, detail=f"上下文 JSON 不符合 Schema：{str(exc)[:200]}") from exc
        return UploadResponse(context=demo_store.replace_context(context), message="上下文 JSON 已导入")
    context = demo_store.context()
    from app.schemas.models import KnowledgeItem

    context.knowledge_base.append(KnowledgeItem(title=file.filename or "导入知识", content=content[:20000], tags=["imported", "custom"]))
    return UploadResponse(context=demo_store.replace_context(context), message="知识文件已加入 Knowledge Base")


@router.post("/events/trigger", response_model=TriggerResponse)
@router.post("/agent/run", response_model=TriggerResponse)
def trigger_event(request: TriggerRequest) -> TriggerResponse:
    state = demo_store.context()
    event = request.event
    if event.source in state.sensors:
        state.sensors[event.source].status = "triggered"
        state.sensors[event.source].value = event.data
    if event.type == "device" and "online" in event.data:
        device = DeviceRegistry(state.devices).for_event_source(event.source, event.target_person_id)
        if device:
            device.online = bool(event.data["online"])
            device.status = "ready" if event.data["online"] else "offline"
            device.state["status"] = device.status
    if event.source == "door_sensor" and event.data.get("open"):
        state.environment.door_state = "open"
    decision = current_orchestrator().run(state, event)
    saved = demo_store.replace_context(state)
    demo_store.remember_decision(decision, event)
    return TriggerResponse(context=saved, decision=decision)


@router.post("/goals/{goal_id}/feedback", response_model=FeedbackResponse)
def submit_goal_feedback(goal_id: str, submission: FeedbackSubmission) -> FeedbackResponse:
    goal = demo_store.active_goal()
    latest_evaluation = demo_store.latest_goal_evaluation()
    if not goal:
        if latest_evaluation and latest_evaluation.goal_id == goal_id and latest_evaluation.goal_status == CareGoalStatus.COMPLETED:
            raise HTTPException(status_code=409, detail="该 Goal 已完成，不能再次提交 Feedback")
        raise HTTPException(status_code=409, detail="当前没有可接收 Feedback 的 Active Goal")
    if goal.goal_id != goal_id:
        raise HTTPException(status_code=409, detail=f"goal_id 与当前 Active Goal 不一致：{goal.goal_id}")
    if goal.status not in {CareGoalStatus.ACTIVE, CareGoalStatus.AWAITING_FEEDBACK}:
        raise HTTPException(status_code=409, detail=f"当前 Goal 状态 {goal.status.value} 不接受 Feedback")
    if submission.target_person_id and goal.target_person_id and submission.target_person_id != goal.target_person_id:
        raise HTTPException(status_code=422, detail="Feedback Target 与当前 Goal Target 不一致")
    try:
        feedback = FeedbackEvent(goal_id=goal_id, **submission.model_dump())
    except ValidationError as exc:
        message = str(exc.errors()[0].get("msg", "Feedback 数据无效")).replace("Value error, ", "")
        raise HTTPException(status_code=422, detail=message) from exc
    latest_feedback = demo_store.latest_feedback()
    if latest_feedback and (latest_feedback.feedback_type, latest_feedback.source, latest_feedback.target_person_id, latest_feedback.data) == (feedback.feedback_type, feedback.source, feedback.target_person_id, feedback.data):
        raise HTTPException(status_code=409, detail="检测到重复 Feedback，本次提交已拒绝")
    plan = demo_store.active_plan()
    originating_event = demo_store.originating_event()
    previous_risk = demo_store.active_risk_level()
    if not plan or not originating_event or not previous_risk:
        raise HTTPException(status_code=409, detail="当前 Goal 的运行时上下文不完整，请重新触发原始事件")
    try:
        response = FeedbackCoordinator().run(demo_store.context(), goal, plan, originating_event, feedback, previous_risk)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.updated_context = demo_store.replace_context(response.updated_context, clear_runtime=False)
    demo_store.record_feedback(feedback, response.goal_evaluation, response.updated_goal, response.follow_up_plan)
    return response


@router.get("/agent/{decision_id}")
def get_decision(decision_id: str):
    decision = demo_store.decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="未找到该决策")
    return decision


@router.get("/memory")
def memory():
    context = demo_store.context()
    return {"working_memory": context.working_memory, "episodic_memory": context.episodic_memory}


@router.get("/profile")
def profile():
    return demo_store.context().user_profile


@router.post("/reset", response_model=ContextState)
def reset(preset_id: str = "new-user") -> ContextState:
    try:
        return demo_store.reset(preset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
