import type { SceneAnimationModel, SceneDevice } from "@/lib/sceneAnimation";

const icon: Record<string, string> = { light: "☼", door_lock: "▣", smart_screen: "▱", watch: "⌁", phone: "▯", robot: "H" };

export function HarmonyDeviceMarker({ device }: { device: SceneDevice }) {
  if (device.deviceType === "robot" || device.deviceType === "phone" || device.deviceType === "watch") return null;
  return <div className={`dt-device device-${device.deviceType} device-at-${device.location} ${device.active ? "is-matched" : ""} ${device.successful ? "is-success" : ""} ${!device.online ? "is-offline" : ""}`}>
    <span>{icon[device.deviceType]}</span><div><b>{device.label}</b><small>{device.detail}</small></div>
  </div>;
}

export function RemoteGuardian({ devices, notification }: { devices: SceneDevice[]; notification?: string }) {
  const phone = devices.find((device) => device.deviceType === "phone");
  return <aside className={`dt-remote ${phone?.active ? "is-active" : ""}`}>
    <span className="dt-remote-kicker">REMOTE GUARDIAN</span>
    <div className="dt-phone"><i/><b>监护人手机</b><small>{phone?.online === false ? "离线" : "在线"}</small></div>
    {notification ? <div className="dt-notification"><em>CARE ALERT</em><b>{notification.slice(0, 42)}</b><small>家庭协同通知</small></div> : <p>等待家庭协同消息</p>}
  </aside>;
}

export function DeviceEffects({ model }: { model: SceneAnimationModel }) {
  return <>
    {model.watchActive && <div className="dt-watch-effect"><i/>Watch 正在提醒</div>}
    {model.screenMessage && <div className="dt-screen-message"><span>HARMONY SCREEN</span><b>{model.screenMessage.slice(0, 28)}</b></div>}
  </>;
}
