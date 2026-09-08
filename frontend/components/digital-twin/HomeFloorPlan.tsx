"use client";

import type { SceneAnimationModel } from "@/lib/sceneAnimation";
import { PersonAvatar } from "./PersonAvatar";
import { RobotAvatar } from "./RobotAvatar";
import { RobotPath } from "./RobotPath";
import { SensorMarker } from "./SensorMarker";
import { DeviceEffects, HarmonyDeviceMarker, RemoteGuardian } from "./HarmonyDeviceMarker";

const rooms = [
  { id: "living_room", name: "客厅", en: "日常活动区", furniture: <><i className="furniture sofa"/><i className="furniture table"/></> },
  { id: "bedroom", name: "卧室", en: "休息区", furniture: <><i className="furniture bed"/><i className="furniture bedside"/></> },
  { id: "entrance", name: "玄关", en: "出入口", furniture: <><i className="furniture entrance-door"/><i className="furniture cabinet"/></> },
  { id: "hallway", name: "走廊", en: "通行区", furniture: <i className="furniture runner"/> },
  { id: "kitchen", name: "厨房", en: "生活区", furniture: <><i className="furniture counter"/><i className="furniture dining"/></> },
];

export function HomeFloorPlan({ model, stage, night }: { model: SceneAnimationModel; stage: number; night: boolean }) {
  return <div className={`dt-map ${night ? "is-night" : ""}`}>
    <div className="dt-floor">
      <RobotPath points={model.robot.path} active={stage === 5 && model.robot.state === "moving"}/>
      {rooms.map((room) => {
        const people = model.people.filter((person) => person.location === room.id);
        const risk = model.roomRisks[room.id] || "normal";
        const light = model.roomLights[room.id];
        return <section key={room.id} className={`dt-room room-${room.id} risk-${risk} ${light === true ? "light-on" : light === false ? "light-off" : ""}`}>
          <header><span>{room.en}</span><b>{room.name}</b></header>
          {room.furniture}
          <div className="dt-room-people">{people.map((person, index) => <PersonAvatar key={person.personId} person={person} index={index}/>)}</div>
          {risk !== "normal" && <div className="dt-risk-label"><i/> {risk === "high" ? "高风险" : "需关注"}</div>}
        </section>;
      })}
      <SensorMarker sensor={model.activeSensor}/>
      {model.devices.map((device) => <HarmonyDeviceMarker key={device.deviceId} device={device}/>)}
      <RobotAvatar robot={model.robot} stage={stage}/>
      <DeviceEffects model={model}/>
      {model.dataFlow && <div className="dt-data-flow"><i/><span>{stage === 1 ? "传感器 → 世界模型" : "上下文 → 语义状态"}</span></div>}
      {model.doorLocked !== null && <div className={`dt-door-lock ${model.doorLocked ? "locked" : "unlocked"} ${model.doorConfirmed ? "confirmed" : ""}`}><span>{model.doorLocked ? "▣" : "□"}</span><b>{model.doorConfirmed ? "已锁定 ✓ · 保持锁定" : model.doorLocked ? "已锁定" : "未锁定"}</b></div>}
    </div>
    <RemoteGuardian devices={model.devices} notification={model.phoneNotification}/>
  </div>;
}
