import type { CareEvent } from "./types";

export type CompetitionSceneId = "elder-fall" | "child-door";

export type CompetitionScene = {
  id: CompetitionSceneId;
  query: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  targetName: string;
  targetPersonId: "elder_li" | "child_xiaoyu";
  historyId: "family_30d_stable";
  historyLabel: string;
  event: CareEvent;
  flow: string[];
};

export const COMPETITION_SCENES: Record<CompetitionSceneId, CompetitionScene> = {
  "elder-fall": {
    id: "elder-fall",
    query: "elder-fall",
    eyebrow: "场景 A · 老人看护",
    title: "老人夜间疑似跌倒",
    subtitle: "具身机器人 + 家庭灯光 + 智能手表 + 手机闭环看护",
    targetName: "李爷爷",
    targetPersonId: "elder_li",
    historyId: "family_30d_stable",
    historyLabel: "30 天稳定家庭",
    event: { type: "sensor", source: "fall_detector", target_person_id: "elder_li", person: "grandpa", data: { detected: true, location: "bedroom" } },
    flow: ["感知跌倒", "开灯", "机器人前往现场", "手表 / 手机联动", "老人反馈", "风险重新评估"],
  },
  "child-door": {
    id: "child-door",
    query: "child-door",
    eyebrow: "场景 B · 儿童看护",
    title: "儿童独处陌生敲门",
    subtitle: "机器人 + 门锁 + 智慧屏 + 智能手表 + 手机安全协同",
    targetName: "小宇",
    targetPersonId: "child_xiaoyu",
    historyId: "family_30d_stable",
    historyLabel: "30 天稳定家庭",
    event: { type: "sensor", source: "door_sensor", target_person_id: "child_xiaoyu", person: "child", data: { open: true, visitor: "unknown", guardian_absent: true, location: "entrance" } },
    flow: ["门口异常", "门锁保持", "机器人主动保护", "智慧屏 / 手表 / 手机协同", "家长确认", "闭环结束"],
  },
};

export const competitionSceneList = Object.values(COMPETITION_SCENES);

export function competitionSceneFromQuery(value: string | null): CompetitionSceneId {
  return value === "child-door" ? "child-door" : "elder-fall";
}
