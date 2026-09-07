"use client";

import { useMemo, useState } from "react";
import type { CareEvent, Context } from "@/lib/types";

type Props = { context: Context; event: CareEvent; onSave: (context: Context) => Promise<void>; onUpload: (file: File) => Promise<void> };
const SAMPLE = `{
  "schema_version": "1.0",
  "title": "自定义家庭场景",
  "description": "版本化完整场景示例",
  "source": "upload",
  "context": {
    "working_memory": [], "episodic_memory": [], "user_profile": {},
    "knowledge_base": [], "devices": {}, "sensors": {},
    "environment": { "lighting": "bright", "occupancy": {}, "door_state": "closed", "notes": [] }
  },
  "event": { "type": "environment", "source": "manual", "person": "unknown", "data": { "note": "状态发生变化" } }
}`;

export function ContextPanel({ context, event, onSave, onUpload }: Props) {
  const people = Object.values(context.people);
  const [personId, setPersonId] = useState(people.find((person) => person.role === "elder")?.person_id || people[0]?.person_id || "");
  const selectedPerson = context.people[personId] || people[0];
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const summary = useMemo(() => [
    ["人物工作记忆", people.reduce((total, person) => total + person.working_memory.length, 0)],
    ["人物事件记忆", people.reduce((total, person) => total + person.episodic_memory.length, 0)],
    ["人物长期画像", people.reduce((total, person) => total + Object.keys(person.user_profile).length, 0)],
    ["当前传感器", Object.keys(context.sensors).length],
    ["家庭终端", Object.keys(context.devices).length],
    ["知识规则", context.knowledge_base.length],
  ] as const, [context, people]);

  const beginEdit = () => { setDraft(JSON.stringify(context, null, 2)); setEditing(true); setError(""); };
  const commit = async () => {
    try { await onSave(JSON.parse(draft) as Context); setEditing(false); }
    catch (err) { setError(err instanceof Error ? err.message : "JSON 格式不正确"); }
  };
  const copySample = async () => { await navigator.clipboard.writeText(SAMPLE); setCopied(true); window.setTimeout(() => setCopied(false), 1600); };

  return <><section className="family-context-overview glass">
    <div className="panel-heading"><div><span className="eyebrow">HOUSEHOLD CONTEXT</span><h2>{context.household.name}</h2></div><span className="small muted">{people.length} 位家庭成员 · {context.active_history || "兼容场景"}</span></div>
    <div className="person-tabs">{people.map((person) => <button key={person.person_id} className={selectedPerson?.person_id === person.person_id ? "active" : ""} onClick={() => setPersonId(person.person_id)}><b>{person.name}</b><small>{person.role === "elder" ? "老人" : "儿童"}</small></button>)}</div>
    {selectedPerson && <div className="person-memory-grid"><article><small>当前画像</small><p>{Object.values(selectedPerson.user_profile).map((item) => `${item.field}: ${String(item.value)}`).join(" · ") || "仅有基础身份，尚未形成长期画像"}</p></article><article><small>Working Memory</small><p>{selectedPerson.working_memory.slice(-3).map((item) => item.content).join("；") || "暂无工作记忆"}</p></article><article><small>近期 Episodes</small><p>{selectedPerson.episodic_memory.slice(-3).map((item) => item.event).join("；") || "暂无事件记忆"}</p></article></div>}
    <div className="history-detail-row"><details><summary>查看完整历史</summary><div className="full-history-list">{selectedPerson?.episodic_memory.length ? selectedPerson.episodic_memory.slice().reverse().map((episode) => <p key={episode.id}><time>{new Date(episode.timestamp).toLocaleString("zh-CN")}</time><b>{episode.event}</b><span>{episode.location} · {episode.result}</span></p>) : <p>当前人物暂无历史 Episode。</p>}</div></details><details><summary>查看 JSON</summary><pre>{JSON.stringify(context, null, 2)}</pre></details></div>
  </section><details className="advanced-context glass">
    <summary><div><span className="eyebrow">ADVANCED DATA</span><b>高级导入与原始上下文（Context）</b><small>日常演示无需操作；用于自定义数据和格式检查</small></div><span>展开</span></summary>
    <div className="advanced-context-body">
      <section><h3>当前数据概览</h3><div className="context-stat-grid">{summary.map(([label, count]) => <div key={label}><b>{count}</b><span>{label}</span></div>)}</div><div className="event-preview"><span>待处理事件</span><b>{event.type === "conversation" ? String(event.data.text || "用户对话") : `${event.source} 状态变化`}</b></div><button className="context-edit-button" onClick={beginEdit}>编辑 Context JSON</button></section>
      <section><h3>导入文件</h3><p>完整场景 JSON 可同时导入 Context 与 Event；旧版纯 Context JSON 仍然兼容。TXT/MD 会作为家庭知识规则加入。</p><label className="upload-control upload-control-large"><input type="file" accept=".json,.txt,.md" onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}/><span>选择 JSON / TXT / MD 文件</span><small>UTF-8 编码 · 最大 1 MB</small></label><div className="sample-links"><a href="/samples/harmony-care-scenario-v1.json" download>下载完整场景示例</a><a href="/samples/family-rule.md" download>下载知识文件示例</a></div></section>
      <section className="format-example"><div><h3>完整场景格式</h3><button onClick={copySample}>{copied ? "已复制" : "复制示例"}</button></div><pre>{SAMPLE}</pre></section>
    </div>
    {editing && <div className="context-modal" role="dialog" aria-modal="true" aria-label="Context JSON 编辑器"><div className="context-modal-card"><header><div><span className="eyebrow">SCHEMA VALIDATION</span><b>Context JSON 编辑器</b></div><button aria-label="关闭编辑器" onClick={() => setEditing(false)}>×</button></header><textarea value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false}/>{error && <p className="error">{error}</p>}<button className="primary wide" onClick={commit}>校验并应用上下文</button></div></div>}
  </details></>;
}
