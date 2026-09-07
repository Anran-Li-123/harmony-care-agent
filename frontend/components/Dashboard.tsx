"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CareEvent, Context, Decision, HistoryOption, Preset, ScenarioDraft, ScenarioGenerationRequest, ScenarioOptions } from "@/lib/types";
import { SiteHeader } from "./SiteHeader";
import { ScenarioComposer } from "./ScenarioComposer";
import { SmartHomeScene } from "./SmartHomeScene";
import { Pipeline } from "./Pipeline";
import { DevicePanel } from "./DevicePanel";
import { DecisionPanel } from "./DecisionPanel";
import { ContextPanel } from "./ContextPanel";
import { MemoryEvolution } from "./MemoryEvolution";
import { HistorySelector } from "./HistorySelector";
import { HouseholdEventSelector } from "./HouseholdEventSelector";
import { WorldStatePanel } from "./WorldStatePanel";

type PlaybackStatus = "idle" | "playing" | "paused" | "complete";
const finalStage = 7;

export function Dashboard() {
  const [context, setContext] = useState<Context | null>(null);
  const [beforeContext, setBeforeContext] = useState<Context | null>(null);
  const [resultContext, setResultContext] = useState<Context | null>(null);
  const [draft, setDraft] = useState<ScenarioDraft | null>(null);
  const [event, setEvent] = useState<CareEvent | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
  const [histories, setHistories] = useState<HistoryOption[]>([]);
  const [options, setOptions] = useState<ScenarioOptions | null>(null);
  const [activePreset, setActivePreset] = useState("night-fall");
  const [decision, setDecision] = useState<Decision | null>(null);
  const [stage, setStage] = useState(-1);
  const [playback, setPlayback] = useState<PlaybackStatus>("idle");
  const [speed, setSpeed] = useState(1);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [runtime, setRuntime] = useState<{ mock_mode: boolean; model: string }>({ mock_mode: true, model: "qwen3.8-flash" });

  const resetPlayback = useCallback(() => {
    setBeforeContext(null);
    setResultContext(null);
    setDecision(null);
    setStage(-1);
    setPlayback("idle");
  }, []);

  const applyDraft = useCallback((next: ScenarioDraft) => {
    setDraft(next);
    setContext(next.context);
    setEvent(next.event);
    setActivePreset(next.context.active_preset);
    resetPlayback();
  }, [resetPlayback]);

  useEffect(() => { void (async () => {
    try {
      const [loadedPresets, loadedOptions, legacyDraft, health, loadedHistories] = await Promise.all([api.presets(), api.scenarioOptions(), api.scenario("night-fall"), api.health(), api.histories()]);
      const initial = await api.loadHistory("family_30d_stable");
      setPresets(loadedPresets); setOptions(loadedOptions); setRuntime(health); setHistories(loadedHistories);
      setDraft({ ...legacyDraft, title: "30天稳定家庭", description: "固定家庭历史已加载，请另行选择本次新事件。", context: initial });
      setContext(initial); setActivePreset(initial.active_preset);
      setEvent({ type: "sensor", source: "fall_detector", target_person_id: "elder_li", person: "grandpa", data: { detected: true, location: "bedroom" } });
      resetPlayback();
    } catch (err) { setError(err instanceof Error ? err.message : "后端不可用。请启动 FastAPI 服务。"); }
  })(); }, [resetPlayback]);

  useEffect(() => {
    if (playback !== "playing") return;
    if (stage >= finalStage) {
      if (resultContext) setContext(resultContext);
      setPlayback("complete");
      setNotice("演示完成：终端反馈、事件记忆与画像变化已同步。");
      return;
    }
    const timer = window.setTimeout(() => setStage((current) => Math.min(current + 1, finalStage)), 900 / speed);
    return () => window.clearTimeout(timer);
  }, [playback, resultContext, speed, stage]);

  const loadPreset = async (presetId: string) => {
    try {
      setBusy(true); setError(""); setNotice("");
      const next = await api.scenario(presetId);
      applyDraft(next); setActivePreset(presetId); setNotice(`已加载：${next.title}`);
    } catch (err) { setError(err instanceof Error ? err.message : "加载场景失败"); }
    finally { setBusy(false); }
  };

  const loadHistory = async (historyId: string) => {
    try {
      setBusy(true); setError(""); setNotice("");
      const next = await api.loadHistory(historyId);
      setContext(next); setActivePreset(next.active_preset);
      setDraft((current) => current ? { ...current, title: histories.find((item) => item.id === historyId)?.label || historyId, description: "固定家庭历史已加载，请另行选择本次新事件。", context: next } : current);
      resetPlayback(); setNotice(`已加载家庭历史：${histories.find((item) => item.id === historyId)?.label || historyId}。未自动运行事件。`);
    } catch (err) { setError(err instanceof Error ? err.message : "加载家庭历史失败"); }
    finally { setBusy(false); }
  };

  const changeEvent = useCallback((next: CareEvent) => {
    setEvent(next); resetPlayback(); setNotice("新事件已准备；家庭历史保持不变。");
  }, [resetPlayback]);

  const generateScenario = async (request: ScenarioGenerationRequest) => {
    try {
      setBusy(true); setError(""); setNotice("");
      const next = await api.generateScenario(request);
      applyDraft(next); setNotice(request.prompt ? "AI 已从受控数据包中构造场景。" : "结构化场景已生成，可检查后运行。");
    } catch (err) { setError(err instanceof Error ? err.message : "场景生成失败"); }
    finally { setBusy(false); }
  };

  const execute = async () => {
    if (!context || !event) return;
    try {
      setBusy(true); setError(""); setNotice(""); resetPlayback();
      const snapshot = structuredClone(context);
      const response = await api.trigger(event);
      setBeforeContext(snapshot); setResultContext(response.context); setDecision(response.decision);
      setContext(snapshot); setStage(0); setPlayback("playing");
    } catch (err) { setError(err instanceof Error ? err.message : "Agent 运行失败"); }
    finally { setBusy(false); }
  };

  const step = () => {
    if (!decision) return;
    const next = Math.min(stage + 1, finalStage);
    setStage(next);
    if (next === finalStage) {
      if (resultContext) setContext(resultContext);
      setPlayback("complete");
    } else setPlayback("paused");
  };

  const replay = () => {
    if (!decision || !beforeContext) return;
    setContext(beforeContext); setStage(0); setPlayback("playing"); setNotice("");
  };

  const upload = async (file: File) => {
    try {
      setBusy(true); setError("");
      const response = await api.upload(file);
      if (response.scenario) applyDraft(response.scenario);
      else {
        setContext(response.context);
        setDraft((current) => current ? { ...current, context: response.context, source: "upload" } : current);
        if (response.event) setEvent(response.event);
        resetPlayback();
      }
      setNotice(response.message);
    } catch (err) { setError(err instanceof Error ? err.message : "导入失败"); }
    finally { setBusy(false); }
  };

  const saveContext = async (next: Context) => {
    try {
      const saved = await api.setContext(next); setContext(saved);
      setDraft((current) => current ? { ...current, context: saved } : current);
      resetPlayback(); setNotice("上下文已通过数据结构校验并保存。");
    } catch (err) { setError(err instanceof Error ? err.message : "上下文保存失败"); }
  };

  if (!context || !draft || !event || !options) return <main className="loading-screen"><div className="pulse-orb"/><h1>正在连接 Harmony Care Agent…</h1>{error && <p>{error}</p>}</main>;

  const sceneResult = stage >= 4 ? resultContext : null;
  const deviceContext = stage >= 5 && resultContext ? resultContext : context;

  return <div className="lab-page">
    <SiteHeader lab />
    <main className="lab-shell">
      <header className="lab-heading">
        <div><span className="section-kicker">在线实验室</span><h1>家庭看护 Agent 场景模拟</h1><p>选择示例或组合数据，运行后逐步观察“感知—判断—协同—记忆”的变化。</p></div>
        <div className="lab-runtime"><span><i/>{runtime.mock_mode ? "稳定演示模式" : "真实模型模式"}</span><small>{runtime.model}</small></div>
      </header>
      <HistorySelector options={histories} active={context.active_history} disabled={busy || playback === "playing"} onSelect={loadHistory}/>
      <details className="legacy-presets glass"><summary>旧版完整示例 / Advanced</summary><section className="preset-station" aria-label="完整示例">
        <div className="preset-station-head"><span>八个完整示例</span><small>选择后会清空上一次动画状态</small></div>
        <div className="preset-list">{presets.map((preset) => <button key={preset.id} className={`${activePreset === preset.id ? "selected" : ""} preset-${preset.tone}`} disabled={busy} onClick={() => loadPreset(preset.id)}><span>{preset.name}</span><small>{preset.description}</small></button>)}</div>
      </section></details>
      {(notice || error) && <div className={`notice lab-notice ${error ? "error" : ""}`} role="status">{error || notice}<button aria-label="关闭提示" onClick={() => { setNotice(""); setError(""); }}>×</button></div>}
      <ContextPanel context={context} event={event} onSave={saveContext} onUpload={upload}/>
      <div className="lab-workspace">
        <div className="lab-input-column"><HouseholdEventSelector context={context} event={event} disabled={busy || playback === "playing"} onChange={changeEvent}/><details className="experimental-builder"><summary>Experimental · 旧版场景构造</summary><ScenarioComposer options={options} draft={draft} event={event} disabled={busy || playback === "playing"} onGenerate={generateScenario} onEventChange={changeEvent}/></details></div>
        <section className="lab-center">
          <SmartHomeScene context={context} resultContext={sceneResult} decision={decision} stage={stage} playback={playback}/>
          <Pipeline active={stage} status={playback} speed={speed} disabled={busy} awaitingFeedback={decision?.care_goal?.status === "awaiting_feedback"} onToggle={() => setPlayback((current) => current === "playing" ? "paused" : current === "paused" ? "playing" : current)} onStep={step} onReplay={replay} onSpeed={setSpeed}/>
          <button className="run-simulation" disabled={busy || playback === "playing"} onClick={execute}>{busy ? "正在准备数据…" : decision && playback === "complete" ? "再次运行当前场景" : "开始运行 Agent 动画"}<span>→</span></button>
        </section>
        <aside className="lab-results">
          <WorldStatePanel world={decision?.world_state} visible={stage >= 2}/>
          <DecisionPanel decision={decision} stage={stage}/>
          <DevicePanel devices={deviceContext.devices} decision={decision} stage={stage}/>
        </aside>
      </div>
      <MemoryEvolution beforeContext={beforeContext || context} context={context} decision={decision} stage={stage}/>
      <footer className="lab-footer">演示数据均为虚构 · 系统不构成医疗诊断、治疗建议或真实看护承诺</footer>
    </main>
  </div>;
}
