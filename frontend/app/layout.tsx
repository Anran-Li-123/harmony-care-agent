import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Harmony Care Agent | 鸿蒙分布式智能陪伴",
  description: "面向一老一小全场景看护的鸿蒙分布式智能陪伴机器人系统 Web 演示。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
