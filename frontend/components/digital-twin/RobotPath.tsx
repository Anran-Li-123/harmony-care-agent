import { motion, useReducedMotion } from "framer-motion";
import type { ScenePoint } from "@/lib/sceneAnimation";

function pathData(points: ScenePoint[]) {
  return points.map((point, index) => `${index ? "L" : "M"} ${point.x * 10} ${point.y * 6}`).join(" ");
}

export function RobotPath({ points, active }: { points: ScenePoint[]; active: boolean }) {
  const reduceMotion = useReducedMotion();
  if (points.length < 2) return null;
  const path = pathData(points);
  return <svg className={`dt-robot-path ${active ? "is-active" : ""}`} viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true">
    <path className="dt-path-base" d={path}/>
    <motion.path className="dt-path-progress" d={path} initial={{ pathLength: 0 }} animate={{ pathLength: active ? 1 : 0 }} transition={reduceMotion ? { duration: .01 } : { duration: .5, ease: "easeOut" }}/>
    {points.map((point, index) => <circle key={`${point.x}-${point.y}`} cx={point.x * 10} cy={point.y * 6} r={index === 0 || index === points.length - 1 ? 8 : 4}/>) }
  </svg>;
}
