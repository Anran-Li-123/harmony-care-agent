import type { SceneAnimationModel } from "@/lib/sceneAnimation";

export function SensorMarker({ sensor }: { sensor?: SceneAnimationModel["activeSensor"] }) {
  if (!sensor) return null;
  const door = sensor.source === "door_sensor";
  return <div className={`dt-sensor sensor-${sensor.location} sensor-${sensor.state}`}><i/><div><b>{door ? "Door Sensor" : "Fall Sensor"}</b><small>{sensor.state === "triggered" ? "TRIGGERED" : "HANDLED"}</small></div></div>;
}
