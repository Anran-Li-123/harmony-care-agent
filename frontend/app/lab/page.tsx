import type { Metadata } from "next";
import { Dashboard } from "@/components/Dashboard";

export const metadata: Metadata = {
  title: "旗舰场景演示 | Harmony Care Agent",
  description: "运行老人跌倒与儿童独处两条旗舰场景，观察具身机器人和鸿蒙全屋设备完成主动看护闭环。",
};

export default function LabPage() {
  return <Dashboard />;
}
