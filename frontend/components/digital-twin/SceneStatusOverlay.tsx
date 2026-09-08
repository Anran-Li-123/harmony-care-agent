import type { SceneAnimationModel } from "@/lib/sceneAnimation";

const goalStatus: Record<string, string> = { active: "进行中", awaiting_feedback: "等待反馈", completed: "已完成", planned: "已规划", cancelled: "已取消" };

export function SceneStatusOverlay({ model, stage }: { model: SceneAnimationModel; stage: number }) {
  return <>
    {model.goal && <div className={`dt-current-goal goal-${model.goal.status}`}><span>当前看护目标</span><div><b>{model.goal.description}</b><em>{model.goal.risk}</em></div><small>{goalStatus[model.goal.status]}</small></div>}
    {model.feedbackText && <div className="dt-feedback-bubble"><span>用户反馈 · {model.feedbackSource}</span><b>{model.feedbackText}</b></div>}
    {model.planSteps.length > 0 && <div className="dt-plan-progress"><span>计划进度</span><div>{model.planSteps.map((step) => <div key={step.step_id} className={`dt-plan-step step-${step.visualStatus}`} style={{ animationDelay: `${step.delay}s` }}><i>{step.visualStatus === "completed" ? "✓" : step.visualStatus === "active" ? "●" : step.visualStatus === "waiting" ? "◌" : "○"}</i><b>{step.description}</b></div>)}</div></div>}
    {stage === 5 && model.actionToasts.length > 0 && <div className="dt-action-stack">{model.actionToasts.slice(0, 8).map((toast) => <div key={toast.id} className={toast.success ? "success" : "failed"} style={{ animationDelay: `${toast.delay}s` }}><i>{toast.success ? "✓" : "!"}</i><span><b>{toast.label}</b><small>{toast.detail}</small></span></div>)}</div>}
    {model.memoryStatus && <div className={`dt-memory-state memory-${model.memoryStatus}`}><span>事件记忆</span><b>{model.memoryStatus === "resolved" ? "待定 → 已解决" : model.memoryStatus === "escalated" ? "待定 → 已升级" : "待定"}</b></div>}
  </>;
}
