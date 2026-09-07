import type { Metadata } from "next";
import { Dashboard } from "@/components/Dashboard";

export const metadata: Metadata = {
  title: "在线实验室 | Harmony Care Agent",
  description: "组合家庭看护上下文，运行 Agent 并观察多终端协同与记忆更新。",
};

export default function LabPage() {
  return <Dashboard />;
}
