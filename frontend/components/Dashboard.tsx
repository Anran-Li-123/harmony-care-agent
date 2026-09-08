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
import { CompetitionDemoPicker } from "./CompetitionDemoPicker";
import { COMPETITION_SCENES, competitionSceneFromQuery, type CompetitionSceneId } from "@/lib/competitionDemo";

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
  const [activeDemo, setActiveDemo] = useState<CompetitionSceneId>("elder-fall");
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
      const requestedDemo = competitionSceneFromQuery(new URLSearchParams(window.location.search).get("demo"));
      const competitionScene = COMPETITION_SCENES[requestedDemo];
      const initial = await api.loadHistory(competitionScene.historyId);
      setPresets(loadedPresets); setOptions(loadedOptions); setRuntime(health); setHistories(loadedHistories);
      setDraft({ ...legacyDraft, title: "30天稳定家庭", description: "固定家庭历史已加载，请另行选择本次新事件。", context: initial });
      setContext(initial); setActivePreset(initial.active_preset); setActiveDemo(requestedDemo);
      setEvent(structuredClone(competitionScene.event));
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

  const selectCompetitionDemo = async (demoId: CompetitionSceneId) => {
    try {
      setBusy(true); setError(""); setNotice("");
      const selected = COMPETITION_SCENES[demoId];
      const next = await api.loadHistory(selected.historyId);
      setContext(next); setActivePreset(next.active_preset); setActiveDemo(demoId);
      setDraft((current) => current ? { ...current, title: selected.historyLabel, description: `${selected.title} 已准备，等待手动开始。`, context: next, event: structuredClone(selected.event) } : current);
      setEvent(structuredClone(selected.event)); resetPlayback();
      window.history.replaceState(null, "", `/lab?demo=${selected.query}`);
      setNotice(`旗舰场景已准备：${selected.title}。Runtime Goal / Feedback 已重置，请点击“开始场景”。`);
    } catch (err) { setError(err instanceof Error ? err.message : "旗舰场景加载失败"); }
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
  const demoStatus = playback === "playing" || playback === "paused" ? "RUNNING" : awaitingGoal ? "WAITING FEEDBACK" : playback === "complete" ? "COMPLETED" : "READY";

  return <div className="lab-page">
    <SiteHeader lab />
    <main className="lab-shell">
      <header className="lab-heading">
        <div><span className="section-kicker">比赛演示模式</span><h1>鸿蒙分布式主动看护演示</h1><p>选择旗舰场景，观察 Home World Model、CareGoal、具身执行与 Feedback Loop。</p></div>
        <div className="lab-runtime"><span><i/>{runtime.mock_mode ? "稳定演示模式" : "真实模型模式"}</span><small>{runtime.model}</small></div>
      </header>
      <CompetitionDemoPicker active={activeDemo} status={demoStatus} disabled={busy || playback === "playing"} onSelect={selectCompetitionDemo}/>
      {(notice || error) && <div className={`notice lab-notice ${error ? "error" : ""}`} role="status">{error || notice}<button aria-label="关闭提示" onClick={() => { setNotice(""); setError(""); }}>×</button></div>}
      <details className="competition-advanced glass"><summary><div><span className="eyebrow">ADVANCED EXPERIMENT</span><b>高级实验</b><small>历史组合、自定义 Event、JSON / TXT / MD、AI 构造与旧 Preset</small></div><span>展开高级控制</span></summary><div className="competition-advanced-body">
        <HistorySelector options={histories} active={context.active_history} disabled={busy || playback === "playing"} onSelect={loadHistory}/>
        <details className="legacy-presets"><summary>旧版八个完整示例</summary><section className="preset-station" aria-label="完整示例"><div className="preset-station-head"><span>旧版 Preset</span><small>选择后会清空上一次动画状态</small></div><div className="preset-list">{presets.map((preset) => <button key={preset.id} className={`${activePreset === preset.id ? "selected" : ""} preset-${preset.tone}`} disabled={busy} onClick={() => loadPreset(preset.id)}><span>{preset.name}</span><small>{preset.description}</small></button>)}</div></section></details>
        <ContextPanel context={context} event={event} onSave={saveContext} onUpload={upload}/>
        <div className="advanced-experiment-grid"><HouseholdEventSelector context={context} event={event} disabled={busy || playback === "playing" || Boolean(awaitingGoal)} onChange={changeEvent}/><ScenarioComposer options={options} draft={draft} event={event} disabled={busy || playback === "playing"} onGenerate={generateScenario} onEventChange={changeEvent}/></div>
      </div></details>
      <div className="lab-workspace">
        <div className="lab-input-column"><section className="demo-guide glass"><span className="eyebrow">DEMO GUIDE</span><h2>{demoStatus === "READY" ? "场景已准备" : demoStatus === "RUNNING" ? "系统正在行动" : demoStatus === "WAITING FEEDBACK" ? "请提交反馈" : "本轮闭环完成"}</h2><p>{demoStatus === "READY" ? "先确认上方场景，再点击“开始场景”。" : demoStatus === "RUNNING" ? "跟随中间时间线观察状态变化。" : demoStatus === "WAITING FEEDBACK" ? "选择本人或监护人的真实反馈，触发目标重评。" : "可切换另一个旗舰场景继续演示。"}</p></section><FeedbackSimulationPanel goal={decision?.care_goal} enabled={playback === "complete"} busy={busy} onSubmit={submitFeedback}/></div>
        <section className="lab-center">
          <SmartHomeScene context={context} resultContext={resultContext} decision={decision} stage={stage} playback={playback} runMode={runMode}/>
          <Pipeline active={stage} status={playback} speed={speed} disabled={busy} awaitingFeedback={awaitingGoal} runMode={runMode} onToggle={() => setPlayback((current) => current === "playing" ? "paused" : current === "paused" ? "playing" : current)} onStep={step} onReplay={replay} onSpeed={setSpeed}/>
          <button className="run-simulation" disabled={busy || playback === "playing" || Boolean(awaitingGoal)} onClick={execute}>{busy ? "正在准备数据…" : awaitingGoal ? "请先提交当前 CareGoal 的反馈" : decision && playback === "complete" ? "重新开始场景" : "开始场景"}<span>→</span></button>
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
