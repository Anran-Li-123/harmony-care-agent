"use client";

import type { Context, Decision } from "@/lib/types";
import { buildSceneAnimation, type SceneRunMode } from "@/lib/sceneAnimation";
import { HomeFloorPlan } from "./digital-twin/HomeFloorPlan";
import { SceneStatusOverlay } from "./digital-twin/SceneStatusOverlay";

type Props = {
  context: Context;
  resultContext: Context | null;
  decision: Decision | null;
  stage: number;
  playback: string;
  runMode: SceneRunMode;
};

export function SmartHomeScene({ context, resultContext, decision, stage, playback, runMode }: Props) {
  const model = buildSceneAnimation({ context, resultContext, decision, stage, runMode });
  const environment = context.environment;
  return <section className="scene scene-v2 digital-twin glass">
    <div className="panel-heading dt-heading">
      <div><span className="eyebrow">2D SEMANTIC HOME DIGITAL TWIN</span><h2>家庭语义数字孪生</h2><p>空间、人物、机器人与 Harmony 设备均由当前家庭状态驱动</p></div>
      <div className={`live-pill ${playback === "playing" ? "running" : ""}`}><i/> {playback === "playing" ? "正在回放" : playback === "paused" ? "已暂停" : playback === "complete" ? "本轮完成" : "家庭在线"}</div>
    </div>
    <div className="dt-stage-shell">
      <div className="dt-environment-bar"><span>{environment.time_of_day}</span><span>{environment.temperature_c.toFixed(0)}℃</span><span>{environment.noise_level === "quiet" ? "安静" : "日常声响"}</span><span>{environment.home_mode === "child-care" ? "儿童看护" : environment.home_mode === "elder-care" ? "老人看护" : "家庭常态"}</span><em>{runMode === "feedback" ? "FEEDBACK RUN" : "INITIAL RUN"}</em></div>
      <HomeFloorPlan model={model} stage={stage} night={environment.lighting === "dark"}/>
      <SceneStatusOverlay model={model} stage={stage}/>
    </div>
    <div className="scene-legend dt-legend"><span><i className="legend-dot robot-color"/>具身机器人</span><span><i className="legend-dot sensor-color"/>当前感知</span><span><i className="legend-dot alert-color"/>后端风险区域</span><span><i className="legend-dot device-color"/>Harmony 协同设备</span><b>Web Mock · 非真实定位 / 医疗判断</b></div>
  </section>;
}
