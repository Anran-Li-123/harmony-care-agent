"use client";

import type { HistoryOption } from "@/lib/types";

export function HistorySelector({ options, active, disabled, onSelect }: { options: HistoryOption[]; active: string | null | undefined; disabled: boolean; onSelect: (id: string) => Promise<void> }) {
  return <section className="history-selector glass">
    <div className="panel-heading"><div><span className="eyebrow">STEP 1 · FAMILY HISTORY</span><h2>选择家庭历史背景</h2></div><span className="small muted">固定 JSON · 不实时生成</span></div>
    <div className="history-option-grid">{options.map((option) => <button key={option.id} className={active === option.id ? "active" : ""} disabled={disabled} onClick={() => onSelect(option.id)}><span>{option.history_span}</span><b>{option.label}</b><p>{option.description}</p><small>{option.episode_count} 条家庭 Episode</small></button>)}</div>
  </section>;
}
