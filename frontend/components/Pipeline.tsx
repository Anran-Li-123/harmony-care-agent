"use client";

const initialStages = [
  { en: "Event", title: "事件触发", description: "发生新的家庭事件" },
  { en: "Perception", title: "感知传递", description: "接收传感器与设备变化" },
  { en: "Home World Model", title: "家庭空间世界模型", description: "整合人物、房间与设备状态" },
  { en: "Safety & Planning", title: "安全与目标规划", description: "判断风险并建立 CareGoal" },
  { en: "Harmony Capability", title: "鸿蒙设备能力", description: "寻找当前可用设备能力" },
  { en: "Embodied Execution", title: "具身执行", description: "机器人联合全屋设备行动" },
  { en: "Feedback & Evaluation", title: "反馈与目标评估", description: "等待反馈并重新评估目标" },
  { en: "Memory Evolution", title: "记忆演化", description: "记录结果并更新长期上下文" },
];
const feedbackStages = [
  { en: "Feedback Event", title: "反馈事件", description: "接收本人或监护人反馈" },
  { en: "State Update", title: "状态更新", description: "刷新人物与空间状态" },
  { en: "Goal Evaluation", title: "目标评估", description: "评估 CareGoal 是否达成" },
  { en: "Follow-up Plan", title: "后续规划", description: "生成下一步 Agent Plan" },
  { en: "Capability Matching", title: "能力匹配", description: "匹配可用鸿蒙设备能力" },
  { en: "Embodied Execution", title: "后续具身执行", description: "执行继续、收束或升级动作" },
  { en: "Goal Result", title: "目标结果", description: "确认完成、继续或升级" },
  { en: "Memory Evolution", title: "记忆收束", description: "更新 Episodic Memory" },
];
type Props = { active: number; status: string; speed: number; disabled: boolean; awaitingFeedback?: boolean; runMode?: "initial" | "feedback"; onToggle: () => void; onStep: () => void; onReplay: () => void; onSpeed: (speed: number) => void };

export function Pipeline({ active, status, speed, disabled, awaitingFeedback, runMode = "initial", onToggle, onStep, onReplay, onSpeed }: Props) {
  const canControl = active >= 0;
  const stages = runMode === "feedback" ? feedbackStages : initialStages.map((stage, index) => index === 6 && !awaitingFeedback ? { ...stage, title: "目标结果", description: "确认本轮 CareGoal 结果" } : stage);
  return <section className="pipeline pipeline-v2 glass">
    <div className="panel-heading"><div><span className="eyebrow">PLAYBACK TIMELINE</span><h2>Agent 动画进度</h2></div><span className="small muted">展示证据与结果，不展示隐藏推理</span></div>
    <div className="pipeline-track">{stages.map((stage, index) => <div className="pipe-wrap" key={stage.en}><div className={`pipe-node ${index <= active ? "done" : ""} ${index === active ? "current" : ""}`}><b>{index + 1}</b><small>{stage.en}</small><span>{stage.title}</span><p>{stage.description}</p></div>{index < stages.length - 1 && <i className={index < active ? "line-on" : ""}/>}</div>)}</div>
    <div className="playback-controls" aria-label="动画播放控制">
      <button disabled={disabled || !canControl || status === "complete"} onClick={onToggle}>{status === "playing" ? "暂停" : "继续"}</button>
      <button disabled={disabled || !canControl || status === "playing" || status === "complete"} onClick={onStep}>单步</button>
      <button disabled={disabled || !canControl} onClick={onReplay}>重播</button>
      <label>速度<select aria-label="动画速度" value={speed} onChange={(e) => onSpeed(Number(e.target.value))}><option value={0.75}>0.75×</option><option value={1}>1×</option><option value={1.5}>1.5×</option><option value={2}>2×</option></select></label>
    </div>
  </section>;
}
