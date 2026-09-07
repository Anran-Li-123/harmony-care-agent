"use client";

import { motion } from "framer-motion";
import type { Context, Decision } from "@/lib/types";

type Props = { context: Context; resultContext: Context | null; decision: Decision | null; stage: number; playback: string };
const locations: Record<string, { left: string; top: string }> = { living_room: { left: "26%", top: "38%" }, bedroom: { left: "74%", top: "38%" }, entrance: { left: "15%", top: "78%" }, kitchen: { left: "72%", top: "76%" } };
const roomNames: Record<string, string> = { living_room: "客厅", bedroom: "卧室", entrance: "玄关", kitchen: "厨房" };

function occupant(context: Context, id: string) {
  const people = context.environment.occupancy[id] || [];
  const member = Object.values(context.people).find((person) => people.includes(person.person_id) || people.includes(person.role === "elder" ? "grandpa" : "child"));
  if (member) return { label: member.name, mark: member.role === "elder" ? "老" : "小" };
  return null;
}

export function SmartHomeScene({ context, resultContext, decision, stage, playback }: Props) {
  const visualContext = resultContext || context;
  const robot = visualContext.devices.robot;
  const robotPoint = locations[robot?.location || "living_room"];
  const fall = stage >= 1 && visualContext.sensors.fall_detector?.status === "triggered";
  const door = stage >= 1 && visualContext.sensors.door_sensor?.status === "triggered";
  const watchAlert = stage >= 1 && ["watch_activity", "watch_geofence"].some((key) => visualContext.sensors[key]?.status === "triggered");
  const dataMoving = stage >= 1 && stage <= 5;
  const highRisk = stage >= 3 && decision?.risk_level === "high";
  const speech = stage >= 5 ? robot?.speech : undefined;

  return <section className="scene scene-v2 glass">
    <div className="panel-heading"><div><span className="eyebrow">LIVE HOME SIMULATION</span><h2>家庭实时动画</h2></div><div className={`live-pill ${playback === "playing" ? "running" : ""}`}><i/> {playback === "playing" ? "正在回放" : playback === "paused" ? "已暂停" : playback === "complete" ? "演示完成" : "等待运行"}</div></div>
    <div className={`home-map home-map-v2 ${context.environment.lighting === "dark" ? "night" : ""} ${highRisk ? "risk-map" : ""}`}>
      <div className="home-status-strip"><span>{context.environment.time_of_day}</span><span>{context.environment.temperature_c.toFixed(0)}℃</span><span>{context.environment.noise_level === "quiet" ? "安静" : "日常声响"}</span><span>{context.environment.home_mode === "normal" ? "普通模式" : context.environment.home_mode === "child-care" ? "儿童看护" : "老人看护"}</span></div>
      <svg className={`data-routes ${dataMoving ? "active" : ""}`} viewBox="0 0 800 430" aria-hidden="true"><path d="M610 155 C520 185 470 230 390 250 S240 280 150 330"/><path d="M610 155 C670 230 680 300 710 355"/><circle cx="610" cy="155" r="5"/><circle cx="150" cy="330" r="5"/><circle cx="710" cy="355" r="5"/></svg>
      {Object.entries(roomNames).map(([id, label]) => {
        const person = occupant(context, id);
        const riskRoom = highRisk && ((fall && id === "bedroom") || (door && id === "entrance"));
        return <div key={id} className={`room room-${id} ${riskRoom ? "room-risk" : ""}`}><span>{label}</span><small>{person?.label || "当前无人"}</small>{person && <div className="person-token" aria-label={person.label}><b>{person.mark}</b><i/></div>}</div>;
      })}
      <div className={`sensor-marker fall-marker ${fall ? "alert" : ""}`}><span/><b>跌倒感知</b></div>
      <div className={`sensor-marker door-marker ${door ? "alert" : ""}`}><span/><b>门磁</b></div>
      <div className={`sensor-marker watch-marker ${watchAlert ? "alert" : ""}`}><span/><b>手表状态</b></div>
      <motion.div className="robot robot-placeholder" animate={robotPoint} transition={{ type: "spring", stiffness: 55, damping: 15 }}><span>H</span><label>机器人概念终端</label>{speech && <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="speech">{speech}</motion.div>}</motion.div>
      {highRisk && <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="scene-alert">安全策略已接管</motion.div>}
      {stage >= 2 && stage < 4 && <div className="context-orbit"><i/><span>正在汇集记忆、环境与设备状态</span></div>}
    </div>
    <div className="scene-legend"><span><i className="legend-dot robot-color"/>机器人行动</span><span><i className="legend-dot sensor-color"/>感知数据</span><span><i className="legend-dot alert-color"/>安全状态</span><b>机器人形象为功能占位</b></div>
  </section>;
}
