"use client";

const initialStages = ["事件触发", "感知传递", "世界模型", "安全 / 目标规划", "Harmony 能力匹配", "具身协同执行", "等待反馈", "记忆暂存"];
const feedbackStages = ["反馈事件", "状态更新", "目标评估", "后续规划", "能力匹配", "后续执行", "目标结果", "记忆收束"];
type Props = { active: number; status: string; speed: number; disabled: boolean; awaitingFeedback?: boolean; runMode?: "initial" | "feedback"; onToggle: () => void; onStep: () => void; onReplay: () => void; onSpeed: (speed: number) => void };

export function Pipeline({ active, status, speed, disabled, awaitingFeedback, runMode = "initial", onToggle, onStep, onReplay, onSpeed }: Props) {
  const canControl = active >= 0;
  const stages = runMode === "feedback" ? feedbackStages : initialStages.map((label, index) => index === 6 && !awaitingFeedback ? "目标结果" : label);
  return <section className="pipeline pipeline-v2 glass">
    <div className="panel-heading"><div><span className="eyebrow">PLAYBACK TIMELINE</span><h2>Agent 动画进度</h2></div><span className="small muted">展示证据与结果，不展示隐藏推理</span></div>
    <div className="pipeline-track">{stages.map((stage, index) => <div className="pipe-wrap" key={stage}><div className={`pipe-node ${index <= active ? "done" : ""} ${index === active ? "current" : ""}`}><b>{index + 1}</b><span>{stage}</span></div>{index < stages.length - 1 && <i className={index < active ? "line-on" : ""}/>}</div>)}</div>
    <div className="playback-controls" aria-label="动画播放控制">
      <button disabled={disabled || !canControl || status === "complete"} onClick={onToggle}>{status === "playing" ? "暂停" : "继续"}</button>
      <button disabled={disabled || !canControl || status === "playing" || status === "complete"} onClick={onStep}>单步</button>
      <button disabled={disabled || !canControl} onClick={onReplay}>重播</button>
      <label>速度<select aria-label="动画速度" value={speed} onChange={(e) => onSpeed(Number(e.target.value))}><option value={0.75}>0.75×</option><option value={1}>1×</option><option value={1.5}>1.5×</option><option value={2}>2×</option></select></label>
    </div>
  </section>;
}
