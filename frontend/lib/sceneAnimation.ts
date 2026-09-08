import type {
  Action,
  CareGoalStatus,
  Context,
  Decision,
  Device,
  DeviceExecutionResult,
  DeviceType,
  PersonContext,
  PersonWorldState,
  PlanStep,
  Risk,
  WorldState,
} from "./types";

export type SceneRunMode = "initial" | "feedback";
export type RobotVisualState = "idle" | "moving" | "observing" | "speaking" | "waiting";
export type RoomRisk = "normal" | "concern" | "high";
export type ScenePoint = { x: number; y: number };

export type ScenePerson = {
  personId: string;
  role: "elder" | "child";
  name: string;
  location: string;
  status: string;
  responsive: string;
  stateLabel: string;
  highlighted: boolean;
};

export type SceneDevice = {
  deviceId: string;
  deviceType: DeviceType;
  location: string;
  online: boolean;
  active: boolean;
  successful: boolean;
  label: string;
  detail: string;
};

export type ScenePlanStep = Pick<PlanStep, "step_id" | "description" | "intent"> & {
  visualStatus: "planned" | "active" | "completed" | "waiting";
  delay: number;
};

export type SceneAnimationModel = {
  people: ScenePerson[];
  roomRisks: Record<string, RoomRisk>;
  roomLights: Record<string, boolean>;
  robot: {
    from: string;
    to: string;
    state: RobotVisualState;
    path: ScenePoint[];
    speech?: string;
    waitingText?: string;
  };
  devices: SceneDevice[];
  doorLocked: boolean | null;
  doorConfirmed: boolean;
  screenMessage?: string;
  phoneNotification?: string;
  watchActive: boolean;
  activeSensor?: { source: string; location: string; label: string; state: "triggered" | "handled" };
  dataFlow: boolean;
  feedbackText?: string;
  feedbackSource?: string;
  goal?: {
    description: string;
    status: CareGoalStatus;
    risk: string;
  };
  planSteps: ScenePlanStep[];
  actionToasts: Array<{ id: string; label: string; detail: string; success: boolean; delay: number }>;
  memoryStatus?: "pending" | "resolved" | "escalated";
};

type BuildSceneInput = {
  context: Context;
  resultContext: Context | null;
  decision: Decision | null;
  stage: number;
  runMode: SceneRunMode;
};

const ROOM_POINTS: Record<string, ScenePoint> = {
  living_room: { x: 27, y: 32 },
  bedroom: { x: 75, y: 32 },
  entrance: { x: 19, y: 75 },
  hallway: { x: 50, y: 72 },
  kitchen: { x: 80, y: 75 },
};

const capabilityLabel: Record<string, string> = {
  switch: "灯光已开启",
  navigate_to: "机器人前往现场",
  observe: "机器人现场观察",
  speak: "机器人语音陪伴",
  vibrate: "手表提醒",
  request_confirmation: "手表请求确认",
  push_notification: "监护人收到通知",
  lock: "门锁保持锁定",
  show_message: "智慧屏安全提示",
  display_status: "智慧屏状态更新",
  wait: "机器人留在现场",
  show_status: "监护人终端状态更新",
};

const personStatusLabel: Record<string, string> = {
  normal: "状态正常",
  suspected_fall: "疑似跌倒",
  responsive: "已确认回应",
  needs_help: "明确需要帮助",
  needs_confirmation: "等待状态确认",
  activity_detected_needs_confirmation: "检测到活动，仍需确认",
  safety_concern: "安全关注",
  safe_waiting_for_guardian: "安全等待大人处理",
  outside_safe_zone: "已离开安全区",
};

function deviceById(context: Context, deviceId?: string | null): Device | undefined {
  if (!deviceId) return undefined;
  return Object.values(context.devices).find((device) => device.device_id === deviceId || device.id === deviceId);
}

function resultFor(results: DeviceExecutionResult[], action: Action): DeviceExecutionResult | undefined {
  return results.find((result) => result.device_id === action.target_device_id && result.capability === (action.capability || action.action));
}

function successfulAction(decision: Decision | null, capability: string, deviceId?: string): Action | undefined {
  return decision?.actions.find((action) => {
    if ((action.capability || action.action) !== capability) return false;
    if (deviceId && action.target_device_id !== deviceId) return false;
    return Boolean(resultFor(decision.execution_results, action)?.success);
  });
}

function peopleFrom(context: Context, world: WorldState | null | undefined, useWorld: boolean): ScenePerson[] {
  const source: Array<PersonContext | PersonWorldState> = useWorld && world ? Object.values(world.people) : Object.values(context.people);
  const targetId = world?.active_event?.target_person_id;
  return source.map((person) => ({
    personId: person.person_id,
    role: person.role,
    name: person.name,
    location: person.location || "living_room",
    status: person.status,
    responsive: person.responsive,
    stateLabel: personStatusLabel[person.status] || person.status,
    highlighted: person.person_id === targetId,
  }));
}

function navigationPath(from: string, to: string): ScenePoint[] {
  const start = ROOM_POINTS[from] || ROOM_POINTS.living_room;
  const end = ROOM_POINTS[to] || start;
  if (from === to) return [start];
  const hallway = ROOM_POINTS.hallway;
  return [start, { x: (start.x + hallway.x) / 2, y: 52 }, hallway, { x: (hallway.x + end.x) / 2, y: 52 }, end];
}

function feedbackText(decision: Decision | null): string | undefined {
  const feedback = decision?.feedback;
  if (!feedback) return undefined;
  if (feedback.feedback_type === "user_response") {
    return ({ im_fine: "我没事。", need_help: "我需要帮助。", cannot_stand: "我站不起来。" } as Record<string, string>)[String(feedback.data.response)];
  }
  if (feedback.feedback_type === "no_response") return "暂未收到回应";
  if (feedback.feedback_type === "watch_activity") return "Watch 检测到重新活动";
  if (feedback.feedback_type === "guardian_confirmation") return feedback.data.decision === "rejected" ? "访客未获确认" : "家长已确认访客";
  return "家长暂未回应";
}

function goalRisk(decision: Decision, runMode: SceneRunMode, stage: number): string {
  if (runMode === "feedback" && decision.goal_evaluation && stage >= 3) {
    const evaluation = decision.goal_evaluation;
    return `${evaluation.previous_risk_level.toUpperCase()} → ${evaluation.updated_risk_level.toUpperCase()}`;
  }
  return decision.risk_level.toUpperCase();
}

function visualGoalStatus(decision: Decision, runMode: SceneRunMode, stage: number): CareGoalStatus {
  if (runMode === "feedback" && stage < 6) return decision.previous_goal_status || "awaiting_feedback";
  return decision.care_goal?.status || "active";
}

function roomRisks(decision: Decision | null, runMode: SceneRunMode, stage: number): Record<string, RoomRisk> {
  if (!decision) return {};
  const sourceWorld = runMode === "feedback" ? decision.previous_world_state || decision.world_state : decision.world_state;
  const risks = Object.fromEntries((sourceWorld?.risk_areas || []).map((area) => [area.location, area.risk_indicator])) as Record<string, RoomRisk>;
  if (runMode === "feedback" && decision.goal_evaluation && stage >= 6) {
    const updated = decision.goal_evaluation.updated_risk_level;
    for (const location of Object.keys(risks)) risks[location] = updated === "high" ? "high" : updated === "medium" ? "concern" : "normal";
  }
  return risks;
}

function planSteps(decision: Decision | null, stage: number): ScenePlanStep[] {
  if (!decision?.agent_plan || stage < 3) return [];
  return decision.agent_plan.steps.map((step, index) => {
    let visualStatus: ScenePlanStep["visualStatus"] = "planned";
    if (stage === 3 && index === 0) visualStatus = "active";
    if (stage === 4 && index <= 1) visualStatus = index === 0 ? "completed" : "active";
    if (stage === 5) visualStatus = step.status === "awaiting_feedback" ? "waiting" : "active";
    if (stage >= 6) visualStatus = step.status === "awaiting_feedback" ? "waiting" : step.status === "completed" ? "completed" : "active";
    return { step_id: step.step_id, description: step.description, intent: step.intent, visualStatus, delay: index * 0.22 };
  });
}

function sceneDevices(context: Context, decision: Decision | null, stage: number): SceneDevice[] {
  const visible = stage >= 4;
  return Object.values(context.devices).map((device) => {
    const action = decision?.actions.find((item) => item.target_device_id === device.device_id);
    const result = action && decision ? resultFor(decision.execution_results, action) : undefined;
    const capability = action?.capability || action?.action || "";
    return {
      deviceId: device.device_id,
      deviceType: device.device_type,
      location: device.location || "remote",
      online: device.online,
      active: Boolean(visible && action),
      successful: Boolean(stage >= 5 && result?.success),
      label: device.name,
      detail: capabilityLabel[capability] || capability || (device.online ? "待命" : "离线"),
    };
  });
}

function deviceMessage(decision: Decision | null, capabilities: string[]): string | undefined {
  const action = decision?.actions.find((item) => capabilities.includes(item.capability || item.action || "") && resultFor(decision.execution_results, item)?.success);
  if (!action) return undefined;
  return String(action.parameters.text || action.parameters.message || action.parameters.status || "");
}

export function buildSceneAnimation({ context, resultContext, decision, stage, runMode }: BuildSceneInput): SceneAnimationModel {
  const result = resultContext || context;
  const peopleWorld = runMode === "feedback" && stage < 1 ? decision?.previous_world_state : decision?.world_state;
  const people = peopleFrom(context, peopleWorld, Boolean(peopleWorld));
  const targetId = decision?.care_goal?.target_person_id;
  people.forEach((person) => { person.highlighted = person.personId === targetId; });

  const navigate = decision?.actions.find((action) => (action.capability || action.action) === "navigate_to");
  const navigateResult = navigate && decision ? resultFor(decision.execution_results, navigate) : undefined;
  const robotBefore = context.devices.robot?.location || "living_room";
  const plannedTarget = decision?.agent_plan?.steps.flatMap((step) => step.capability_requests).find((request) => request.capability === "navigate_to")?.target_location;
  const robotAfter = result.devices.robot?.location || plannedTarget || robotBefore;
  const moving = stage === 5 && Boolean(navigateResult?.success);
  const hasObserve = Boolean(successfulAction(decision, "observe"));
  const hasSpeak = Boolean(successfulAction(decision, "speak"));
  const status = decision ? visualGoalStatus(decision, runMode, stage) : "active";
  let robotState: RobotVisualState = "idle";
  if (moving) robotState = "moving";
  else if (stage === 5 && hasObserve) robotState = "observing";
  else if (stage === 5 && hasSpeak) robotState = "speaking";
  else if (stage >= 6 && status === "awaiting_feedback") robotState = "waiting";
  else if (stage >= 6 && Boolean(successfulAction(decision, "wait"))) robotState = "waiting";

  const roomLights: Record<string, boolean> = {};
  for (const device of Object.values(context.devices).filter((item) => item.device_type === "light")) {
    const applied = stage >= 5 && Boolean(successfulAction(decision, "switch", device.device_id));
    const after = deviceById(result, device.device_id);
    roomLights[device.location || "hallway"] = applied ? after?.state.power === "on" : device.state.power === "on";
  }

  const doorBefore = Object.values(context.devices).find((device) => device.device_type === "door_lock");
  const doorAfter = doorBefore ? deviceById(result, doorBefore.device_id) : undefined;
  const doorAction = doorBefore ? successfulAction(decision, "lock", doorBefore.device_id) : undefined;
  const doorLocked = doorBefore ? (stage >= 5 && doorAction ? doorAfter?.state.locked !== false : doorBefore.state.locked !== false) : null;
  const activeWorld = runMode === "feedback" ? decision?.previous_world_state : decision?.world_state;
  const activeEvent = activeWorld?.active_event;

  const toasts = stage === 5 && decision ? decision.actions.map((action, index) => {
    const resultItem = resultFor(decision.execution_results, action);
    const capability = action.capability || action.action || "action";
    const device = deviceById(result, action.target_device_id) || deviceById(context, action.target_device_id);
    return { id: `${action.target_device_id}-${capability}-${index}`, label: capabilityLabel[capability] || capability, detail: device?.name || action.target_device_id || "家庭设备", success: Boolean(resultItem?.success), delay: index * 0.24 };
  }) : [];

  const latestEpisode = targetId ? result.people[targetId]?.episodic_memory.at(-1) : undefined;
  return {
    people,
    roomRisks: roomRisks(decision, runMode, stage),
    roomLights,
    robot: {
      from: robotBefore,
      to: stage >= 5 && navigateResult?.success ? robotAfter : robotBefore,
      state: robotState,
      path: navigationPath(robotBefore, robotAfter),
      speech: stage >= 5 && hasSpeak ? deviceMessage(decision, ["speak"]) : undefined,
      waitingText: stage >= 6 && status === "awaiting_feedback" ? (targetId?.includes("child") ? "等待家长确认" : "等待本人反馈") : undefined,
    },
    devices: sceneDevices(stage >= 5 ? result : context, decision, stage),
    doorLocked,
    doorConfirmed: Boolean(stage >= 5 && doorAction),
    screenMessage: stage >= 5 ? deviceMessage(decision, ["show_message", "display_status"]) : undefined,
    phoneNotification: stage >= 5 ? deviceMessage(decision, ["push_notification", "show_status"]) : undefined,
    watchActive: stage >= 5 && Boolean(decision?.actions.some((action) => ["vibrate", "request_confirmation"].includes(action.capability || "") && resultFor(decision.execution_results, action)?.success)),
    activeSensor: activeEvent ? { source: activeEvent.source, location: decision?.world_state?.sensors[activeEvent.source]?.location || (activeEvent.source === "door_sensor" ? "entrance" : "bedroom"), label: decision?.world_state?.sensors[activeEvent.source]?.label || activeEvent.source, state: stage >= 5 || runMode === "feedback" ? "handled" : "triggered" } : undefined,
    dataFlow: stage === 1 || stage === 2,
    feedbackText: runMode === "feedback" && stage >= 0 ? feedbackText(decision) : undefined,
    feedbackSource: decision?.feedback?.source,
    goal: decision?.care_goal && stage >= 3 ? { description: decision.care_goal.description, status, risk: goalRisk(decision, runMode, stage) } : undefined,
    planSteps: planSteps(decision, stage),
    actionToasts: toasts,
    memoryStatus: stage >= 7 ? latestEpisode?.status : undefined,
  };
}

export { ROOM_POINTS };
