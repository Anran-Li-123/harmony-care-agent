"use client";

import { useState } from "react";

type Props = { disabled: boolean; onTrigger: (event: Record<string, unknown>) => Promise<void>; onGenerate: (prompt: string) => Promise<void> };

export function EventComposer({ disabled, onTrigger, onGenerate }: Props) {
  const [text, setText] = useState("我一个人有点无聊。");
  const [sample, setSample] = useState("生成一个老人夜间独处场景");
  return <section className="event-composer glass"><div className="panel-heading"><div><span className="eyebrow">NEW EVENT</span><h2>发生新事件</h2></div></div><textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="输入用户对话或事件描述…"/><div className="event-buttons"><button disabled={disabled} onClick={() => onTrigger({ type: "conversation", source: "user_voice", person: "grandpa", data: { text, location: "living_room" } })}>▶ 触发对话</button><button disabled={disabled} onClick={() => onTrigger({ type: "sensor", source: "fall_detector", person: "grandpa", data: { detected: true, location: "bedroom" } })}>⚠ 跌倒感知</button><button disabled={disabled} onClick={() => onTrigger({ type: "sensor", source: "door_sensor", person: "child", data: { open: true, location: "entrance" } })}>◉ 门磁打开</button></div><div className="generate-row"><input value={sample} onChange={(e) => setSample(e.target.value)} aria-label="AI 生成样例提示"/><button className="subtle" disabled={disabled} onClick={() => onGenerate(sample)}>✦ AI Generate Sample</button></div></section>;
}
