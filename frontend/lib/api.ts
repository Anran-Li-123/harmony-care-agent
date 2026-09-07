import type { CareEvent, Context, Decision, Preset, ScenarioDraft, ScenarioGenerationRequest, ScenarioOptions } from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...(init?.headers || {}) } });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new Error(problem.detail || `服务请求失败 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; mock_mode: boolean; model: string }>("/api/health"),
  presets: () => request<Preset[]>("/api/demo/presets"),
  scenarioOptions: () => request<ScenarioOptions>("/api/demo/scenario-options"),
  scenario: (presetId: string) => request<ScenarioDraft>(`/api/demo/scenarios/${presetId}`),
  context: () => request<Context>("/api/context"),
  setContext: (context: Context) => request<Context>("/api/context", { method: "POST", body: JSON.stringify(context) }),
  reset: (presetId: string) => request<Context>(`/api/reset?preset_id=${presetId}`, { method: "POST" }),
  generate: (prompt: string) => request<Context>("/api/context/generate", { method: "POST", body: JSON.stringify({ prompt }) }),
  generateScenario: (input: ScenarioGenerationRequest) => request<ScenarioDraft>("/api/scenarios/generate", { method: "POST", body: JSON.stringify(input) }),
  trigger: (event: Record<string, unknown>) => request<{ context: Context; decision: Decision }>("/api/events/trigger", { method: "POST", body: JSON.stringify({ event }) }),
  upload: async (file: File) => {
    const form = new FormData(); form.append("file", file);
    const response = await fetch(`${BASE}/api/context/upload`, { method: "POST", body: form });
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "导入失败");
    return response.json() as Promise<{ context: Context; message: string; event?: CareEvent; scenario?: ScenarioDraft }>;
  },
};
