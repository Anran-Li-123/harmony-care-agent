"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ROOM_POINTS, type SceneAnimationModel } from "@/lib/sceneAnimation";

export function RobotAvatar({ robot, stage }: { robot: SceneAnimationModel["robot"]; stage: number }) {
  const reduceMotion = useReducedMotion();
  const points = robot.state === "moving" ? robot.path : [ROOM_POINTS[robot.to] || ROOM_POINTS.living_room];
  const x = points.map((point) => `${point.x}%`);
  const y = points.map((point) => `${point.y}%`);
  return <motion.div
    className={`dt-robot robot-${robot.state}`}
    initial={false}
    animate={{ left: x, top: y }}
    transition={reduceMotion ? { duration: .01 } : { delay: robot.state === "moving" ? .42 : 0, duration: robot.state === "moving" ? 1.45 : .55, ease: "easeInOut" }}
    aria-label={`陪伴机器人，${robot.state}`}
  >
    <div className="dt-robot-scan"/>
    <div className="dt-robot-head"><span/><span/><i/></div>
    <div className="dt-robot-body"><b>H</b><i/></div>
    <div className="dt-robot-base"><i/><i/></div>
    <small>{robot.state === "moving" ? "MOVING" : robot.state === "observing" ? "OBSERVING" : robot.state === "speaking" ? "SPEAKING" : robot.state === "waiting" ? "WAITING" : "READY"}</small>
    {robot.speech && stage >= 5 && <motion.div className="dt-speech" initial={{ opacity: 0, scale: reduceMotion ? 1 : .9, y: reduceMotion ? 0 : 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} transition={reduceMotion ? { duration: .01 } : { delay: robot.state === "moving" ? 1.65 : .15 }}>{robot.speech}</motion.div>}
    {robot.waitingText && <div className="dt-waiting"><i/>{robot.waitingText}</div>}
  </motion.div>;
}
