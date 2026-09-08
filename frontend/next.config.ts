import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "path";

// Next loads env files from its own directory by default. Load the shared project
// root file first so both the frontend and backend use the same source of truth.
loadEnvConfig(path.resolve(__dirname, ".."));

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  },
};
export default nextConfig;
