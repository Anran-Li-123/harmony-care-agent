"use client";

import { useEffect, useMemo, useState } from "react";
import type { CareEvent, ScenarioDraft, ScenarioGenerationRequest, ScenarioOption, ScenarioOptions } from "@/lib/types";

type Props = {
  options: ScenarioOptions;
  draft: ScenarioDraft;
  event: CareEvent;
  disabled: boolean;
  onGenerate: (request: ScenarioGenerationRequest) => Promise<void>;
  onEventChange: (event: CareEvent) => void;
};

const presetSelections: Record<string, ["elder" | "child", string, string, string]> = {
  "new-user": ["elder", "blank", "daytime-normal", "elder-intro"],
  "night-fall": ["elder", "routine", "elder-night", "fall"],
  "elder-watch-inactive": ["elder", "routine", "wearable-alert", "watch-inactive"],
  "child-door": ["child", "stable", "child-home-alone", "door-open"],
  "child-safe-zone": ["child", "routine", "wearable-alert", "safe-zone"],
  companion: ["elder", "stable", "daytime-normal", "elder-companion"],
  "habit-change": ["elder", "changing", "elder-night", "sleep-review"],
  "device-offline": ["elder", "stable", "device-degraded", "device-offline"],
};

function available(items: ScenarioOption[], persona: "elder" | "child") {
  return items.filter((item) => item.compatible_personas.includes(persona));
}

const eventSourceText: Record<string, string> = { user_voice: "用户语音", fall_detector: "跌倒感知器", door_sensor: "入口门磁", watch_activity: "手表活动状态", watch_geofence: "手表安全区", profile_observer: "作息记录观察器", watch: "家庭手表", phone: "监护人手机", manual: "手动环境记录" };

export function ScenarioComposer({ options, draft, event, disabled, onGenerate, onEventChange }: Props) {
  const [persona, setPersona] = useState<"elder" | "child">(event.person === "child" ? "child" : "elder");
  const [memory, setMemory] = useState("blank");
  const [state, setState] = useState("daytime-normal");
  const [trigger, setTrigger] = useState(event.person === "child" ? "child-chat" : "elder-intro");
  const [prompt, setPrompt] = useState("生成一个老人夜间独处、只有手表状态变化的场景");

  const memoryOptions = useMemo(() => available(options.memory_packs, persona), [options, persona]);
  const stateOptions = useMemo(() => available(options.state_packs, persona), [options, persona]);
  const triggerOptions = useMemo(() => available(options.trigger_packs, persona), [options, persona]);

  useEffect(() => {
    const selection = presetSelections[draft.context.active_preset];
    if (!selection) return;
    setPersona(selection[0]); setMemory(selection[1]); setState(selection[2]); setTrigger(selection[3]);
  }, [draft.context.active_preset]);

  useEffect(() => {
    if (!memoryOptions.some((item) => item.id === memory)) setMemory(memoryOptions[0]?.id || "blank");
    if (!stateOptions.some((item) => item.id === state)) setState(stateOptions[0]?.id || "daytime-normal");
    if (!triggerOptions.some((item) => item.id === trigger)) setTrigger(triggerOptions[0]?.id || "child-chat");
  }, [memory, memoryOptions, state, stateOptions, trigger, triggerOptions]);

  const request = (withPrompt: boolean): ScenarioGenerationRequest => ({
    persona_pack: persona,
    memory_pack: memory,
    state_pack: state,
    trigger_pack: trigger,
    ...(withPrompt ? { prompt: prompt.trim() } : {}),
  });

  const eventText = String(event.data.text || "");
  const sourceLabel = { preset: "完整示例", template: "结构化组合", ai: "AI 构造", fallback: "稳定模板回退", upload: "文件导入" }[draft.source];

  return <section className="scenario-composer glass">
    <div className="panel-heading"><div><span className="eyebrow">SCENARIO BUILDER</span><h2>构造本次家庭场景</h2></div><span className={`source-chip source-${draft.source}`}>{sourceLabel}</span></div>
    <div className="scenario-current"><b>{draft.title}</b><p>{draft.description}</p>{draft.warnings.map((warning) => <span key={warning}>提示：{warning}</span>)}</div>
    <div className="persona-switch" aria-label="选择用户类型">
      <button className={persona === "elder" ? "active" : ""} onClick={() => setPersona("elder")} disabled={disabled}>老人用户</button>
      <button className={persona === "child" ? "active" : ""} onClick={() => setPersona("child")} disabled={disabled}>儿童用户</button>
    </div>
    <div className="scenario-fields">
      <label><span>1 · 记忆底稿</span><select value={memory} onChange={(e) => setMemory(e.target.value)} disabled={disabled}>{memoryOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select><small>{memoryOptions.find((item) => item.id === memory)?.description}</small></label>
      <label><span>2 · 当前状态</span><select value={state} onChange={(e) => setState(e.target.value)} disabled={disabled}>{stateOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select><small>{stateOptions.find((item) => item.id === state)?.description}</small></label>
      <label><span>3 · 新输入或变化</span><select value={trigger} onChange={(e) => setTrigger(e.target.value)} disabled={disabled}>{triggerOptions.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select><small>{triggerOptions.find((item) => item.id === trigger)?.description}</small></label>
    </div>
    <button className="builder-button" disabled={disabled} onClick={() => onGenerate(request(false))}>生成结构化场景</button>
    <div className="ai-builder"><label htmlFor="scenario-prompt">让 AI 选择一组受控数据</label><textarea id="scenario-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={disabled}/><button disabled={disabled || !prompt.trim()} onClick={() => onGenerate(request(true))}>✦ AI 构造场景</button></div>
    <div className="incoming-event">
      <div><span>本次输入</span><b>{event.type === "conversation" ? "用户对话" : "无对话 · 状态变化"}</b></div>
      {event.type === "conversation" ? <textarea aria-label="编辑本次用户对话" value={eventText} onChange={(e) => onEventChange({ ...event, data: { ...event.data, text: e.target.value } })}/> : <p>{eventSourceText[event.source] || event.source} · {JSON.stringify(event.data)}</p>}
    </div>
  </section>;
}
