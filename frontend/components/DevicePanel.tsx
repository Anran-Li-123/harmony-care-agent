"use client";

import type { Decision, Device, DeviceType } from "@/lib/types";

const groupLabel: Record<string, string> = { embodied: "具身终端", personal: "个人设备", household: "家庭设备" };
const typeLabel: Record<DeviceType, string> = { robot: "机器人", watch: "手表", phone: "手机", light: "灯光", door_lock: "门锁", smart_screen: "智慧屏" };
const capabilityLabel: Record<string, string> = { navigate_to: "前往现场", speak: "语音提醒", observe: "现场观察", vibrate: "震动提醒", show_message: "显示消息", request_confirmation: "请求确认", push_notification: "推送通知", switch: "开关", set_brightness: "调节亮度", lock: "保持锁定", get_status: "读取状态", display_status: "显示状态", start_call: "发起通话", play_audio: "播放内容", wait: "保持观察" };

function stateText(device: Device) {
  if (device.device_type === "light") return device.state.power === "on" ? `已开启 · ${String(device.state.brightness ?? 100)}%` : "已关闭";
  if (device.device_type === "door_lock") return device.state.locked === false ? "未锁定" : "已锁定";
  if (device.device_type === "smart_screen") return device.state.display === "idle" ? "待机" : `显示：${String(device.state.display)}`;
  return device.status === "ready" ? "待命" : device.status || "待命";
}

function DeviceCard({ device, decision, visible }: { device: Device; decision: Decision | null; visible: boolean }) {
  const actions = decision?.actions.filter((item) => item.target_device_id === device.device_id) || [];
  const action = actions[actions.length - 1];
  const results = decision?.execution_results?.filter((item) => item.device_id === device.device_id) || [];
  const result = results[results.length - 1];
  const capability = action?.capability || action?.action;
  return <article className={`capability-device ${visible && action ? "device-active" : ""}`}>
    <div className="capability-device-head"><span className={`device-type-icon type-${device.device_type}`}>{typeLabel[device.device_type].slice(0, 1)}</span><div><b>{device.name}</b><small>{device.device_id}</small></div><i className={device.online ? "online" : "offline"}/></div>
    <div className="device-meta"><span>{device.location || device.owner || "家庭"}</span><span>{stateText(device)}</span><span>{device.latest_action || "待命"}</span></div>
    <p>{visible && capability ? `${capabilityLabel[capability] || capability} · ${result?.message || "等待执行"}` : "等待能力匹配"}</p>
    {visible && result && <em className={result.success ? "result-success" : "result-failed"}>{result.success ? "执行成功" : "执行失败"}</em>}
  </article>;
}

export function DevicePanel({ devices, decision, stage }: { devices: Record<string, Device>; decision: Decision | null; stage: number }) {
  const all = Object.values(devices);
  const groups = {
    embodied: all.filter((device) => device.device_type === "robot"),
    household: all.filter((device) => ["light", "door_lock", "smart_screen"].includes(device.device_type)),
    personal: all.filter((device) => ["watch", "phone"].includes(device.device_type)),
  };
  const visible = stage >= 5;
  return <section className="terminal-feedback glass">
    <div className="panel-heading"><div><span className="eyebrow">结果反馈 · 鸿蒙设备</span><h2>分布式设备能力</h2></div><span className="small muted">网页仿真</span></div>
    {(Object.keys(groups) as Array<keyof typeof groups>).map((group) => <div className="device-capability-group" key={group}><h3>{groupLabel[group]} <small>{groups[group].length}</small></h3><div className="device-capability-grid">{groups[group].map((device) => <DeviceCard key={device.device_id} device={device} decision={decision} visible={visible}/>)}</div></div>)}
  </section>;
}
