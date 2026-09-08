import type { ScenePerson } from "@/lib/sceneAnimation";

export function PersonAvatar({ person, index = 0 }: { person: ScenePerson; index?: number }) {
  return <div className={`dt-person person-${person.role} ${person.highlighted ? "is-target" : ""} ${person.status !== "normal" ? "has-state" : ""}`} style={{ "--person-index": index } as React.CSSProperties} aria-label={`${person.name}，${person.stateLabel}`}>
    <div className="dt-person-avatar" aria-hidden="true"><span>{person.role === "elder" ? "👴" : "🧒"}</span><i/></div>
    <div className="dt-person-label"><b>{person.name}</b><small>{person.stateLabel}</small>{person.role === "elder" && <em className="dt-wearable">⌁ 智能手表</em>}</div>
  </div>;
}
