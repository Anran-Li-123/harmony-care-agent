"use client";

import { useState } from "react";
import type { CareEvent, Context } from "@/lib/types";

type Target = "elder_li" | "child_xiaoyu" | "household";
type EventTemplate = { id: string; label: string; event: CareEvent };

const templates: Record<Target, EventTemplate[]> = {
  elder_li: [
    { id: "elder-fall", label: "Fall Sensor", event: { type: "sensor", source: "fall_detector", target_person_id: "elder_li", person: "grandpa", data: { detected: true, location: "bedroom" } } },
    { id: "elder-watch", label: "Watch Inactivity", event: { type: "sensor", source: "watch_activity", target_person_id: "elder_li", person: "grandpa", data: { still_minutes: 45, acknowledged: false, location: "bedroom" } } },
    { id: "elder-afraid", label: "我有点害怕", event: { type: "conversation", source: "user_voice", target_person_id: "elder_li", person: "grandpa", data: { text: "我有点害怕。", location: "living_room" } } },
    { id: "elder-bored", label: "我有点无聊", event: { type: "conversation", source: "user_voice", target_person_id: "elder_li", person: "grandpa", data: { text: "我一个人有点无聊。", location: "living_room" } } },
  ],
  child_xiaoyu: [
    { id: "child-door", label: "陌生人敲门 / Doorbell", event: { type: "sensor", source: "door_sensor", target_person_id: "child_xiaoyu", person: "child", data: { open: true, visitor: "unknown", guardian_absent: true, location: "entrance" } } },
    { id: "child-zone", label: "Leave Safe Zone", event: { type: "sensor", source: "watch_geofence", target_person_id: "child_xiaoyu", person: "child", data: { inside: false, zone: "家庭安全区" } } },
    { id: "child-afraid", label: "我害怕", event: { type: "conversation", source: "user_voice", target_person_id: "child_xiaoyu", person: "child", data: { text: "门外有人，我有点害怕。", location: "living_room" } } },
    { id: "child-chat", label: "普通陪伴", event: { type: "conversation", source: "user_voice", target_person_id: "child_xiaoyu", person: "child", data: { text: "陪我聊一会儿吧。", location: "living_room" } } },
  ],
  household: [
    { id: "family-environment", label: "Environment Change", event: { type: "environment", source: "environment_sensor", target_person_id: null, person: null, data: { note: "家庭环境状态发生变化" } } },
    { id: "family-smoke", label: "Smoke Sensor Event", event: { type: "environment", source: "smoke_detector", target_person_id: null, person: null, data: { triggered: true, location: "kitchen" } } },
    { id: "family-robot-offline", label: "Robot Offline", event: { type: "device", source: "robot", target_person_id: null, person: null, data: { online: false } } },
  ],
};

export function HouseholdEventSelector({ context, event, disabled, onChange }: { context: Context; event: CareEvent; disabled: boolean; onChange: (event: CareEvent) => void }) {
  const initialTarget: Target = event.target_person_id === "child_xiaoyu" ? "child_xiaoyu" : event.target_person_id == null ? "household" : "elder_li";
  const [target, setTarget] = useState<Target>(initialTarget);
  const [templateId, setTemplateId] = useState(templates[initialTarget][0].id);
  const chooseTarget = (next: Target) => { setTarget(next); setTemplateId(templates[next][0].id); onChange(structuredClone(templates[next][0].event)); };
  const chooseEvent = (id: string) => { setTemplateId(id); const selected = templates[target].find((item) => item.id === id); if (selected) onChange(structuredClone(selected.event)); };
  const label = event.target_person_id ? context.people[event.target_person_id]?.name || event.target_person_id : "家庭环境";
  return <section className="household-event-selector glass">
    <div className="panel-heading"><div><span className="eyebrow">STEP 3 · NEW EVENT</span><h2>选择本次新事件</h2></div><span className="small muted">历史与 Event 相互独立</span></div>
    <label><span>事件对象</span><select value={target} disabled={disabled} onChange={(e) => chooseTarget(e.target.value as Target)}><option value="elder_li">李爷爷</option><option value="child_xiaoyu">小宇</option><option value="household">家庭环境</option></select></label>
    <label><span>New Event</span><select value={templateId} disabled={disabled} onChange={(e) => chooseEvent(e.target.value)}>{templates[target].map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
    {event.type === "conversation" && <label><span>对话内容</span><textarea value={String(event.data.text || "")} disabled={disabled} onChange={(e) => onChange({ ...event, data: { ...event.data, text: e.target.value } })}/></label>}
    <div className="prepared-event"><span>已准备，尚未运行</span><b>{label} · {event.source}</b></div>
  </section>;
}
