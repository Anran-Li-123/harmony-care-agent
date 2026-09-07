"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CareEvent, Context, Decision, Preset, ScenarioDraft, ScenarioGenerationRequest, ScenarioOptions } from "@/lib/types";
import { SiteHeader } from "./SiteHeader";
import { ScenarioComposer } from "./ScenarioComposer";
import { SmartHomeScene } from "./SmartHomeScene";
import { Pipeline } from "./Pipeline";
import { DevicePanel } from "./DevicePanel";
import { DecisionPanel } from "./DecisionPanel";
import { ContextPanel } from "./ContextPanel";
import { MemoryEvolution } from "./MemoryEvolution";

type PlaybackStatus = "idle" | "playing" | "paused" | "complete";
const finalStage = 7;

export function Dashboard() {
  const [context, setContext] = useState<Context | null>(null);
  const [beforeContext, setBeforeContext] = useState<Context | null>(null);
  const [resultContext, setResultContext] = useState<Context | null>(null);
  const [draft, setDraft] = useState<ScenarioDraft | null>(null);
  const [event, setEvent] = useState<CareEvent | null>(null);
  const [presets, setPresets] = useState<Preset[]>([]);
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
      const [loadedPresets, loadedOptions, initial, health] = await Promise.all([api.presets(), api.scenarioOptions(), api.scenario("night-fall"), api.health()]);
      setPresets(loadedPresets); setOptions(loadedOptions); setRuntime(health); applyDraft(initial);
    } catch (err) { setError(err instanceof Error ? err.message : "后端不可用。请启动 FastAPI 服务。"); }
  })(); }, [applyDraft]);

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
      <section className="preset-station" aria-label="完整示例">
        <div className="preset-station-head"><span>八个完整示例</span><small>选择后会清空上一次动画状态</small></div>
        <div className="preset-list">{presets.map((preset) => <button key={preset.id} className={`${activePreset === preset.id ? "selected" : ""} preset-${preset.tone}`} disabled={busy} onClick={() => loadPreset(preset.id)}><span>{preset.name}</span><small>{preset.description}</small></button>)}</div>
      </section>
      {(notice || error) && <div className={`notice lab-notice ${error ? "error" : ""}`} role="status">{error || notice}<button aria-label="关闭提示" onClick={() => { setNotice(""); setError(""); }}>×</button></div>}
      <div className="lab-workspace">
        <ScenarioComposer options={options} draft={draft} event={event} disabled={busy || playback === "playing"} onGenerate={generateScenario} onEventChange={setEvent}/>
        <section className="lab-center">
          <SmartHomeScene context={context} resultContext={sceneResult} decision={decision} stage={stage} playback={playback}/>
          <Pipeline active={stage} status={playback} speed={speed} disabled={busy} onToggle={() => setPlayback((current) => current === "playing" ? "paused" : current === "paused" ? "playing" : current)} onStep={step} onReplay={replay} onSpeed={setSpeed}/>
          <button className="run-simulation" disabled={busy || playback === "playing"} onClick={execute}>{busy ? "正在准备数据…" : decision && playback === "complete" ? "再次运行当前场景" : "开始运行 Agent 动画"}<span>→</span></button>
        </section>
        <aside className="lab-results">
          <DecisionPanel decision={decision} stage={stage}/>
          <DevicePanel devices={deviceContext.devices} decision={decision} stage={stage}/>
        </aside>
      </div>
      <MemoryEvolution beforeContext={beforeContext || context} context={context} decision={decision} stage={stage}/>
      <ContextPanel context={context} event={event} onSave={saveContext} onUpload={upload}/>
      <footer className="lab-footer">演示数据均为虚构 · 系统不构成医疗诊断、治疗建议或真实看护承诺</footer>
    </main>
  </div>;
}
