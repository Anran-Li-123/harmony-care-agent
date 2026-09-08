"use client";

import type { Context, Decision, Timeline } from "@/lib/types";

function time(value: string) { return new Date(value).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" }); }

export function MemoryEvolution({ beforeContext, context, decision, stage }: { beforeContext: Context; context: Context; decision: Decision | null; stage: number }) {
  const timeline: Timeline[] = decision?.timeline || [];
  const visibleTimeline = stage < 0 ? [] : timeline.slice(0, Math.max(1, Math.ceil(((stage + 1) / 8) * timeline.length)));
  const memoryVisible = stage >= 6;
  return <section className="memory-section memory-section-v2 glass">
    <div className="panel-heading"><div><span className="eyebrow">结果反馈 · 记忆演化</span><h2>记忆与画像如何变化</h2></div><span className="small muted">时间记录不等于长期画像；更新必须有明确或持续证据</span></div>
    <div className="evolution">
      <article><small>运行前</small><b>{Object.keys(beforeContext.user_profile).length ? `${Object.keys(beforeContext.user_profile).length} 条长期画像` : "画像为空"}</b><p>{Object.values(beforeContext.user_profile).slice(0, 2).map((item) => `${item.field}: ${String(item.value)}`).join(" · ") || "允许从完全空白的新用户开始"}</p></article><i>→</i>
      <article className={stage >= 6 ? "changed" : ""}><small>记忆候选</small><b>{memoryVisible ? `${decision?.memory_updates.length || 0} 条候选` : "等待记忆阶段"}</b><p>{memoryVisible ? decision?.memory_updates.map((item) => item.preview).join("；") || "本次无新增记忆" : "智能体完成设备行动后再写入记录"}</p></article><i>→</i>
      <article className={memoryVisible && decision?.profile_changes.length ? "changed" : ""}><small>长期画像</small><b>{memoryVisible ? decision?.profile_changes.length ? "画像已更新" : "保持不变" : "尚未处理"}</b><p>{memoryVisible ? decision?.profile_changes.map((change) => `${change.field}: ${String(change.before ?? "空白")} → ${String(change.after)}`).join("；") || "单次普通状态不会被写成长期偏好" : "只接受明确表达或多条一致证据"}</p></article>
    </div>
    <div className="timeline timeline-v2"><div className="timeline-title">本次运行记录</div>{visibleTimeline.length ? visibleTimeline.map((item) => <div className={`timeline-item ${item.tone}`} key={item.id}><time>{time(item.timestamp)}</time><i/><div><b>{item.title}</b><span>{item.detail}</span></div></div>) : <p className="muted">运行场景后，这里会按动画进度展开完整链路。</p>}</div>
    <div className="episode-strip"><b>最近时间 / 事件记录</b>{context.episodic_memory.length ? context.episodic_memory.slice(-4).reverse().map((episode) => <span key={episode.id}>{episode.event} · {episode.result}</span>) : <span>暂无历史记录</span>}</div>
  </section>;
}
