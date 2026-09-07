"use client";

const stages = ["准备", "感知变化", "上下文汇集", "安全 / AI 判断", "动作路由", "终端反馈", "记忆更新", "完成"];
type Props = { active: number; status: string; speed: number; disabled: boolean; onToggle: () => void; onStep: () => void; onReplay: () => void; onSpeed: (speed: number) => void };

export function Pipeline({ active, status, speed, disabled, onToggle, onStep, onReplay, onSpeed }: Props) {
  const canControl = active >= 0;
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
