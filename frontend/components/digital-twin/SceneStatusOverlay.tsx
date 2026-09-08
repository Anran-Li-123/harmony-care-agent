import type { SceneAnimationModel } from "@/lib/sceneAnimation";

const goalStatus: Record<string, string> = { active: "ACTIVE", awaiting_feedback: "AWAITING FEEDBACK", completed: "COMPLETED", planned: "PLANNED", cancelled: "CANCELLED" };

export function SceneStatusOverlay({ model, stage }: { model: SceneAnimationModel; stage: number }) {
  return <>
    {model.goal && <div className={`dt-current-goal goal-${model.goal.status}`}><span>CURRENT CARE GOAL</span><div><b>{model.goal.description}</b><em>{model.goal.risk}</em></div><small>{goalStatus[model.goal.status]}</small></div>}
    {model.feedbackText && <div className="dt-feedback-bubble"><span>FEEDBACK · {model.feedbackSource}</span><b>{model.feedbackText}</b></div>}
    {model.planSteps.length > 0 && <div className="dt-plan-progress"><span>PLAN PROGRESS</span><div>{model.planSteps.map((step) => <div key={step.step_id} className={`dt-plan-step step-${step.visualStatus}`} style={{ animationDelay: `${step.delay}s` }}><i>{step.visualStatus === "completed" ? "✓" : step.visualStatus === "active" ? "●" : step.visualStatus === "waiting" ? "◌" : "○"}</i><b>{step.description}</b></div>)}</div></div>}
    {stage === 5 && model.actionToasts.length > 0 && <div className="dt-action-stack">{model.actionToasts.slice(0, 8).map((toast) => <div key={toast.id} className={toast.success ? "success" : "failed"} style={{ animationDelay: `${toast.delay}s` }}><i>{toast.success ? "✓" : "!"}</i><span><b>{toast.label}</b><small>{toast.detail}</small></span></div>)}</div>}
    {model.memoryStatus && <div className={`dt-memory-state memory-${model.memoryStatus}`}><span>EPISODE MEMORY</span><b>{model.memoryStatus === "resolved" ? "PENDING → RESOLVED" : model.memoryStatus === "escalated" ? "PENDING → ESCALATED" : "PENDING"}</b></div>}
  </>;
}
