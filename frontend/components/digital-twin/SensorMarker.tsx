import type { SceneAnimationModel } from "@/lib/sceneAnimation";

export function SensorMarker({ sensor }: { sensor?: SceneAnimationModel["activeSensor"] }) {
  if (!sensor) return null;
  const door = sensor.source === "door_sensor";
  return <div className={`dt-sensor sensor-${sensor.location} sensor-${sensor.state}`}><i/><div><b>{door ? "门磁传感器" : "跌倒传感器"}</b><small>{sensor.state === "triggered" ? "已触发" : "已处理"}</small></div></div>;
}
