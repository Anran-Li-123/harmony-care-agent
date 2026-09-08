"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CareEvent, Context, Decision, FeedbackSubmission, HistoryOption, Preset, ScenarioDraft, ScenarioGenerationRequest, ScenarioOptions } from "@/lib/types";
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
import { FeedbackSimulationPanel } from "./FeedbackSimulationPanel";

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
  const [runMode, setRunMode] = useState<"initial" | "feedback">("initial");
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
    setRunMode("initial");
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
      setNotice(runMode === "feedback" ? `反馈闭环完成：${decision?.goal_evaluation?.outcome || "目标状态已更新"}。` : "首轮干预完成：设备结果与 Pending Memory 已同步。需要反馈的 Goal 可继续运行第二轮。");
      return;
    }
    const stageDuration = stage === 5 ? (runMode === "initial" ? 2200 : 1300) : runMode === "feedback" ? 780 : 900;
    const timer = window.setTimeout(() => setStage((current) => Math.min(current + 1, finalStage)), stageDuration / speed);
    return () => window.clearTimeout(timer);
  }, [decision?.goal_evaluation?.outcome, playback, resultContext, runMode, speed, stage]);

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
      setContext(snapshot); setRunMode("initial"); setStage(0); setPlayback("playing");
    } catch (err) { setError(err instanceof Error ? err.message : "Agent 运行失败"); }
    finally { setBusy(false); }
  };

  const submitFeedback = async (input: FeedbackSubmission) => {
    if (!context || !decision?.care_goal) return;
    try {
      setBusy(true); setError(""); setNotice("");
      const snapshot = structuredClone(context);
      const response = await api.feedback(decision.care_goal.goal_id, input);
      const feedbackDecision: Decision = {
        ...decision,
        risk_level: response.goal_evaluation.updated_risk_level,
        summary: response.goal_evaluation.summary,
        evidence: response.goal_evaluation.evidence,
        world_state: response.updated_world_state,
        care_goal: response.updated_goal,
        agent_plan: response.follow_up_plan,
        goal_evaluation: response.goal_evaluation,
        feedback: response.feedback,
        previous_world_state: decision.world_state,
        previous_goal_status: decision.care_goal.status,
        actions: response.actions,
        execution_results: response.execution_results,
        memory_updates: [{ type: "episodic", reason: "同一 Goal 的反馈已评估", preview: response.goal_evaluation.summary }],
        profile_candidates: [], profile_changes: [], timeline: response.timeline,
      };
      setBeforeContext(snapshot); setResultContext(response.updated_context); setDecision(feedbackDecision);
      setContext(snapshot); setRunMode("feedback"); setStage(0); setPlayback("playing");
    } catch (err) { setError(err instanceof Error ? err.message : "Feedback 处理失败"); }
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

  const deviceContext = stage >= 5 && resultContext ? resultContext : context;
  const awaitingGoal = decision?.care_goal?.status === "awaiting_feedback";

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
        <div className="lab-input-column"><HouseholdEventSelector context={context} event={event} disabled={busy || playback === "playing" || Boolean(awaitingGoal)} onChange={changeEvent}/><FeedbackSimulationPanel goal={decision?.care_goal} enabled={playback === "complete"} busy={busy} onSubmit={submitFeedback}/><details className="experimental-builder"><summary>Experimental · 旧版场景构造</summary><ScenarioComposer options={options} draft={draft} event={event} disabled={busy || playback === "playing"} onGenerate={generateScenario} onEventChange={changeEvent}/></details></div>
        <section className="lab-center">
          <SmartHomeScene context={context} resultContext={resultContext} decision={decision} stage={stage} playback={playback} runMode={runMode}/>
          <Pipeline active={stage} status={playback} speed={speed} disabled={busy} awaitingFeedback={awaitingGoal} runMode={runMode} onToggle={() => setPlayback((current) => current === "playing" ? "paused" : current === "paused" ? "playing" : current)} onStep={step} onReplay={replay} onSpeed={setSpeed}/>
          <button className="run-simulation" disabled={busy || playback === "playing" || Boolean(awaitingGoal)} onClick={execute}>{busy ? "正在准备数据…" : awaitingGoal ? "请先提交当前 Goal 的反馈" : decision && playback === "complete" ? "再次运行当前场景" : "开始运行 Agent 动画"}<span>→</span></button>
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
