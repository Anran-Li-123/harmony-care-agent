"use client";

import type { Decision, Device } from "@/lib/types";

const riskLabel = { low: "低风险", medium: "需关注", high: "高优先级" };
const actionLabel: Record<string, string> = { move_to: "前往指定位置", speak: "语音提醒", camera_check: "现场画面确认", vibrate: "手表震动", health_check: "请求状态确认", push_notification: "推送监护通知", play_audio: "播放陪伴内容", wait: "保持观察", ready: "待命" };

export function DevicePanel({ devices, decision, stage }: { devices: Record<string, Device>; decision: Decision | null; stage: number }) {
  const watch = devices.watch;
  const phone = devices.phone;
  const robot = devices.robot;
  const watchAction = decision?.actions.find((action) => action.target === "watch");
  const phoneAction = decision?.actions.find((action) => action.target === "phone");
  const feedbackVisible = stage >= 5;
  return <section className="terminal-feedback glass">
    <div className="panel-heading"><div><span className="eyebrow">DEVICE SCREENS</span><h2>终端反馈画面</h2></div><span className="small muted">阶段 {Math.max(stage + 1, 0)} / 8</span></div>
    <div className="device-screen-grid">
      <article className={`watch-device ${feedbackVisible && watchAction ? "device-active" : ""}`}>
        <div className="watch-crown"/><div className="watch-screen">
          <div className="screen-status"><i className={watch?.online ? "online" : "offline"}/><span>{watch?.online ? "手表在线" : "连接中断"}</span><time>19:30</time></div>
          <strong>{watch?.owner || "家庭成员"}</strong>
          <small>{watch?.wearing === false ? "未佩戴" : "正在佩戴"} · 电量 {watch?.battery ?? 0}%</small>
          <div className={`watch-message ${feedbackVisible && watchAction ? "show" : ""}`}>{feedbackVisible ? watch?.latest_notification || (watchAction ? "请确认当前状态" : "本次无需手表提醒") : "等待 Agent 路由"}</div>
          {feedbackVisible && watchAction && <button tabIndex={-1}>轻触确认</button>}
        </div>
      </article>
      <article className={`phone-device ${feedbackVisible && phoneAction ? "device-active" : ""}`}>
        <div className="phone-speaker"/><div className="phone-screen">
          <div className="phone-appbar"><span>家庭看护</span><i>{phone?.online ? "在线" : "离线"}</i></div>
          <div className="phone-user"><b>{phone?.owner || "监护人"}</b><small>设备电量 {phone?.battery ?? 0}%</small></div>
          <div className={`phone-notification ${feedbackVisible && phoneAction ? "show" : ""}`}><span>{decision ? riskLabel[decision.risk_level] : "等待事件"}</span><b>{feedbackVisible ? phoneAction ? "新的家庭看护反馈" : "本次无需通知" : "Agent 尚未路由到手机"}</b><p>{feedbackVisible ? phone?.latest_notification || "当前事件不需要监护人操作。" : "运行到“终端反馈”阶段后显示消息。"}</p></div>
          <div className="phone-progress"><i className={feedbackVisible ? "done" : ""}/><span>{feedbackVisible ? phoneAction ? "反馈已送达" : "保持安静" : "等待处理"}</span></div>
        </div>
      </article>
    </div>
    <div className="robot-device-row"><span className="robot-mini">H</span><div><b>机器人概念终端</b><small>{feedbackVisible ? actionLabel[robot?.latest_action || "ready"] || robot?.latest_action : "等待动作路由"}</small></div><i className={robot?.online ? "online" : "offline"}/></div>
  </section>;
}
