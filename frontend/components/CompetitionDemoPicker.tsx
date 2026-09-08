"use client";

import { competitionSceneList, type CompetitionSceneId } from "@/lib/competitionDemo";

type DemoStatus = "READY" | "RUNNING" | "WAITING FEEDBACK" | "COMPLETED";

export function CompetitionDemoPicker({ active, status, disabled, onSelect }: {
  active: CompetitionSceneId;
  status: DemoStatus;
  disabled: boolean;
  onSelect: (id: CompetitionSceneId) => Promise<void>;
}) {
  const scene = competitionSceneList.find((item) => item.id === active) || competitionSceneList[0];
  const statusLabel = { READY: "已就绪", RUNNING: "运行中", "WAITING FEEDBACK": "等待反馈", COMPLETED: "已完成" }[status];
  return <section className="competition-demo glass" aria-labelledby="competition-demo-title">
    <div className="competition-demo-head"><div><span className="eyebrow">第 1 步 · 选择场景</span><h2 id="competition-demo-title">旗舰场景演示</h2><p>选择场景只会装载家庭与事件；确认状态为“已就绪”后，再开始完整闭环。</p></div><span className={`demo-status status-${status.toLowerCase().replaceAll(" ", "-")}`}><i/>{statusLabel}</span></div>
    <div className="competition-scene-switch">{competitionSceneList.map((item) => <button key={item.id} className={active === item.id ? "active" : ""} disabled={disabled} onClick={() => onSelect(item.id)}><span>{item.eyebrow}</span><b>{item.title}</b><small>{item.subtitle}</small></button>)}</div>
    <div className="demo-context-strip" aria-label="当前演示状态">
      <div><span>家庭背景</span><b>{scene.historyLabel}</b></div>
      <div><span>当前对象</span><b>{scene.targetName}</b></div>
      <div><span>场景</span><b>{scene.title}</b></div>
      <div><span>模式</span><b>网页仿真</b></div>
      <div><span>状态</span><b>{statusLabel}</b></div>
    </div>
  </section>;
}
