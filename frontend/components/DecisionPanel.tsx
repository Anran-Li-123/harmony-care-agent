"use client";

import type { Decision } from "@/lib/types";

const riskText = { low: "低风险", medium: "需关注", high: "高优先级" };
const goalStatusText = { planned: "PLANNED", active: "ACTIVE", awaiting_feedback: "AWAITING FEEDBACK", completed: "COMPLETED", cancelled: "CANCELLED" };
const actionText: Record<string, string> = { navigate_to: "前往指定位置", speak: "语音提醒", observe: "现场画面确认", vibrate: "手表震动", request_confirmation: "请求状态确认", push_notification: "推送监护通知", play_audio: "播放陪伴内容", wait: "保持观察", switch: "切换灯光", set_brightness: "调节亮度", lock: "保持门锁锁定", get_status: "读取设备状态", show_message: "显示提醒", display_status: "显示家庭状态", start_call: "发起通话" };

function deviceLabel(deviceId?: string | null, legacyTarget?: string | null) {
  if (deviceId?.includes("light")) return "灯光";
  if (deviceId?.includes("lock")) return "门锁";
  if (deviceId?.includes("screen")) return "智慧屏";
  if (deviceId?.includes("watch")) return "手表";
  if (deviceId?.includes("phone")) return "手机";
  if (deviceId?.includes("robot")) return "机器人";
  return legacyTarget === "robot" ? "机器人" : legacyTarget === "watch" ? "手表" : legacyTarget === "phone" ? "手机" : "设备";
}

export function DecisionPanel({ decision, stage }: { decision: Decision | null; stage: number }) {
  if (!decision || stage < 3) return <section className="decision-panel glass empty-decision"><span>{stage >= 0 ? String(Math.min(stage + 1, 3)).padStart(2, "0") : "✦"}</span><h2>{stage < 0 ? "等待运行场景" : stage === 0 ? "准备家庭事件" : stage === 1 ? "读取感知变化" : "汇集可用上下文"}</h2><p>到达判断阶段后，这里会呈现关键证据、家庭规则和可验证的行动结论。</p></section>;
  return <section className={`decision-panel glass risk-${decision.risk_level}`}>
    <div className="decision-top"><div><span className="eyebrow">AGENT DECISION · {decision.llm_mode === "mock" ? "稳定演示" : "真实模型"}</span><h2>Agent 判断</h2></div><div className="risk-badge"><small>风险级别</small><b>{riskText[decision.risk_level]}</b></div></div>
    <p className="decision-summary">{decision.summary}</p>
    {decision.care_goal && <div className="current-goal"><div><span>CURRENT GOAL</span><b>{decision.care_goal.description}</b><small>{decision.care_goal.goal_type}</small></div><strong className={`goal-status status-${decision.care_goal.status}`}>{goalStatusText[decision.care_goal.status]}</strong></div>}
    {decision.goal_evaluation && <div className={`goal-evaluation evaluation-${decision.goal_evaluation.outcome.toLowerCase()}`}><div className="evaluation-head"><span>GOAL EVALUATION</span><b>{decision.goal_evaluation.outcome}</b></div><p>{decision.goal_evaluation.summary}</p><div><strong>Risk {decision.goal_evaluation.previous_risk_level.toUpperCase()} → {decision.goal_evaluation.updated_risk_level.toUpperCase()}</strong><small>Goal {goalStatusText[decision.goal_evaluation.goal_status]}</small></div>{decision.goal_evaluation.evidence.map((item) => <em key={item}>✓ {item}</em>)}</div>}
    {decision.agent_plan && <div className="agent-plan"><div className="agent-plan-title"><b>AGENT PLAN</b><span>{decision.agent_plan.summary}</span></div>{decision.agent_plan.steps.map((step, index) => <div className={`plan-step plan-${step.status}`} key={step.step_id}><i>{step.status === "completed" ? "✓" : step.status === "awaiting_feedback" ? "○" : index + 1}</i><div><b>{step.description}</b><small>{step.intent}{step.required_capability ? ` · ${step.required_capability}` : ""}</small></div></div>)}</div>}
    <div className="evidence"><b>用于判断的关键证据</b>{decision.evidence.map((item) => <span key={item}>✓ {item}</span>)}</div>
    {decision.retrieved_knowledge.length > 0 && <div className="knowledge-hit"><b>命中的家庭规则</b><span>{decision.retrieved_knowledge.join(" · ")}</span></div>}
    <div className={`action-list ${stage < 4 ? "action-pending" : ""}`}><b>计划路由的动作</b>{stage < 4 ? <p>等待进入动作路由阶段…</p> : decision.actions.map((action, index) => { const capability = action.capability || action.action || "unknown"; return <div key={`${action.target_device_id || action.target}-${capability}-${index}`}><span className={`target ${action.target || "home-device"}`}>{deviceLabel(action.target_device_id, action.target)}</span><strong>{actionText[capability] || capability}</strong><em>{action.reason || action.rationale} · {action.target_device_id || "兼容路由"}</em></div>; })}</div>
  </section>;
}
