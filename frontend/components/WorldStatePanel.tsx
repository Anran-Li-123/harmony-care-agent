"use client";

import type { WorldState } from "@/lib/types";

const locationText: Record<string, string> = { bedroom: "卧室", living_room: "客厅", entrance: "玄关", kitchen: "厨房", outdoor: "室外", outside_safe_zone: "安全区外" };
const statusText: Record<string, string> = { normal: "正常", suspected_fall: "疑似跌倒", responsive: "已回应", needs_help: "明确需要帮助", activity_detected_needs_confirmation: "检测到活动，仍需确认", safe_waiting_for_guardian: "安全等待中", needs_confirmation: "需要确认", safety_concern: "安全关注", outside_safe_zone: "已离开安全区", ready: "待命", executing: "执行中", offline: "离线" };
const responsiveText = { normal: "正常", unknown: "未知", confirmed: "已确认回应", unresponsive: "无响应" };
const sourceText: Record<string, string> = { fall_detector: "跌倒感知", door_sensor: "门口事件", watch_activity: "手表长时静止", watch_geofence: "安全区变化", user_voice: "用户语音", smoke_detector: "烟雾感知" };

export function WorldStatePanel({ world, visible }: { world: WorldState | null | undefined; visible: boolean }) {
  if (!world || !visible) return <section className="world-state-panel glass world-waiting"><div className="panel-heading"><div><span className="eyebrow">WORLD STATE</span><h2>当前世界状态</h2></div></div><p>运行 Agent 后，这里展示由 Context 与 Current Event 确定性派生的家庭空间快照。</p></section>;
  return <section className="world-state-panel glass">
    <div className="panel-heading"><div><span className="eyebrow">WORLD STATE · DERIVED</span><h2>当前世界状态</h2></div><span className="small muted">非长期存储</span></div>
    <div className="world-people">{Object.values(world.people).map((person) => <article key={person.person_id} className={`world-person world-${person.status}`}><span>{person.role === "elder" ? "老人" : "儿童"}</span><b>{person.name}</b><p>{locationText[person.location || ""] || person.location || "位置未知"} · {statusText[person.status] || person.status} · 响应：{responsiveText[person.responsive]}</p></article>)}</div>
    {world.robot && <div className="world-robot"><span>Robot</span><b>{locationText[world.robot.location || ""] || world.robot.location || "位置未知"} · {world.robot.online ? statusText[world.robot.status] || world.robot.status : "离线"}</b></div>}
    <div className="world-facts"><div><span>当前风险区域</span><b>{world.risk_areas.length ? world.risk_areas.map((area) => locationText[area.location] || area.location).join("、") : "无"}</b></div><div><span>当前事件</span><b>{world.active_event ? sourceText[world.active_event.source] || world.active_event.source : "无"}</b></div></div>
  </section>;
}
