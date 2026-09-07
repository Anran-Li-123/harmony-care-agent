"use client";

import type { CareGoal, FeedbackSubmission } from "@/lib/types";

type Props = { goal?: CareGoal | null; enabled: boolean; busy: boolean; onSubmit: (input: FeedbackSubmission) => void };

export function FeedbackSimulationPanel({ goal, enabled, busy, onSubmit }: Props) {
  if (!goal?.requires_feedback || goal.status !== "awaiting_feedback") return null;
  const elderGoal = ["confirm_person_safety", "confirm_person_status"].includes(goal.goal_type);
  const childGoal = goal.goal_type === "keep_child_safe_from_unknown_visitor";
  if (!elderGoal && !childGoal) return null;
  const send = (input: FeedbackSubmission) => () => onSubmit(input);
  return <section className="feedback-simulation-panel glass">
    <div className="panel-heading"><div><span className="eyebrow">FEEDBACK EVENT</span><h2>{elderGoal ? "模拟老人反馈" : "模拟监护人反馈"}</h2></div><span className="feedback-waiting">AWAITING</span></div>
    <p>反馈属于当前 Goal，不会创建新的独立看护目标。</p>
    <div className="feedback-buttons">
      {elderGoal && <>
        <button disabled={!enabled || busy} onClick={send({ feedback_type: "user_response", source: "robot_microphone", target_person_id: goal.target_person_id, data: { response: "im_fine" } })}>老人回应：我没事</button>
        <button disabled={!enabled || busy} className="warning" onClick={send({ feedback_type: "user_response", source: "robot_microphone", target_person_id: goal.target_person_id, data: { response: "cannot_stand" } })}>老人回应：我站不起来</button>
        <button disabled={!enabled || busy} className="danger" onClick={send({ feedback_type: "no_response", source: "robot", target_person_id: goal.target_person_id, data: { timeout: true } })}>老人无回应</button>
        <button disabled={!enabled || busy} onClick={send({ feedback_type: "watch_activity", source: "elder_watch_01", target_person_id: goal.target_person_id, data: { activity_detected: true } })}>Watch 检测到重新活动</button>
      </>}
      {childGoal && <>
        <button disabled={!enabled || busy} onClick={send({ feedback_type: "guardian_confirmation", source: "guardian_phone_01", target_person_id: goal.target_person_id, data: { decision: "confirmed" } })}>家长确认访客</button>
        <button disabled={!enabled || busy} className="warning" onClick={send({ feedback_type: "guardian_confirmation", source: "guardian_phone_01", target_person_id: goal.target_person_id, data: { decision: "rejected" } })}>家长拒绝访客</button>
        <button disabled={!enabled || busy} className="danger" onClick={send({ feedback_type: "guardian_no_response", source: "guardian_phone_01", target_person_id: goal.target_person_id, data: { timeout: true } })}>家长暂未回应</button>
      </>}
    </div>
    {!enabled && <small>请先播放完当前一轮设备执行。</small>}
  </section>;
}
