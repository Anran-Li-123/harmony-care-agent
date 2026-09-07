# Harmony Care Agent Demo

《面向“一老一小”全场景看护的鸿蒙分布式智能陪伴机器人系统研发》Web Demo。

这是一个面向大学生创新竞赛的可运行演示：以 AI Agent 为家庭智能中枢，串联**环境感知 → 上下文理解 → 安全决策 → Robot / Watch / Phone 协同 → 记忆更新 → 长期画像演化**。当前的终端是 Web 模拟设备；其适配器边界已预留给未来 HarmonyOS 分布式设备实现。

## 核心设计

```text
Working / Episodic / Profile / Knowledge / Device / Sensor / Environment
                                  + New Event
                                        ↓
ContextAssembler → SafetyPolicy → KnowledgeRetriever → LLMProvider
                                        ↓
                         ActionRouter → Robot | Watch | Phone
                                        ↓
                  MemoryExtractor → ProfileUpdater → New Context
```

- **一套链路支持冷启动和历史用户**：新用户允许空画像、空事件记忆；每次交互仍进入统一的编排流程。
- **事件记忆不等于用户画像**：`MemoryExtractor` 写入工作/事件记忆，`ProfileUpdater` 再基于证据决定画像变化。
- **显式优先，推断克制**：称呼等显式信息可立即保存；京剧、作息等推断需要持续证据；医疗、药物、过敏、紧急联系人等高风险字段不能由一次普通事件推断。
- **安全优先于 LLM**：跌倒、儿童独处时门磁开启等明确信号先由 `SafetyPolicy` 处理，再路由终端动作。
- **真正可替换**：`LLMProvider`、`DeviceAdapter`、内存 Store、Knowledge Retriever 都是清晰边界，后续可换 Redis/PostgreSQL/向量库/HarmonyOS SDK。

## 功能演示

| 预设 | 演示结果 |
| --- | --- |
| 全新老人首次交流 | 自我介绍后创建 Episode，显式学习 `preferred_name = 李爷爷` |
| 老人夜间疑似跌倒 | 卧室跌倒触发，Robot 前往卧室、Watch 震动、Phone 通知家属 |
| 老人手表长时静止 | 请求本人和现场确认、同步监护人，但不作医疗诊断 |
| 儿童独处门磁开启 | 门磁打开，Robot 到入口观察、提醒儿童、通知家长 |
| 儿童离开安全区 | Watch 提醒儿童并将位置状态变化同步给监护人 |
| 老人日常陪伴 | 读取京剧偏好并提供陪伴，不产生紧急推送 |
| 作息习惯逐渐变化 | 三条晚间事件形成持续证据，`sleep_time` 从 `21:30` 更新为 `22:45` |
| 终端离线降级 | Watch 离线后改由 Robot 与 Phone 完成提示与反馈 |

项目首页位于 `/`；在线实验室位于 `/lab`。实验室提供八个完整示例、记忆/状态/事件组合器、受控 AI 场景构造、版本化 JSON 与 TXT/MD 导入、可暂停/单步/重播的家庭动画、手表与手机屏幕，以及 Timeline / Memory Evolution。

## 目录

```text
backend/
  app/
    agent/          # 编排、安全、知识检索、LLM、记忆与画像更新
    devices/        # Mock DeviceAdapter / ActionRouter
    data/           # 五个演示 Preset
    api/            # FastAPI endpoints
    schemas/        # Pydantic 数据契约
    services/       # 可替换的内存 Store
  tests/            # Mock-only API tests，不消耗 LLM token
frontend/
  app/              # Next.js entry 与样式
  components/       # 场景、上下文、管线、终端、事件、记忆 UI
  lib/              # 类型与 API client
```

## 运行

需要 Python 3.10+、Node.js 20+。

```powershell
# Terminal 1
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2
cd frontend
npm install
npm run dev
```

打开 `http://localhost:3000`。后端健康检查为 `http://localhost:8000/api/health`。

## Mock Mode（比赛演示默认）

复制 `backend/.env.example` 为 `backend/.env`，设置：

```env
MOCK_MODE=true
MODEL_NAME=qwen3.8-flash
```

无需 API Key，即可完成所有预设、动画、记忆更新与 API 演示。Mock 决策是可重复的规则输出，适合稳定演示与自动化测试。

## Real LLM Mode（Qwen）

```env
MOCK_MODE=false
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=你的密钥
MODEL_NAME=qwen3.8-flash
FRONTEND_URL=http://localhost:3000
```

后端的 `OpenAICompatibleProvider` 使用 OpenAI Python SDK 的 `chat.completions`；密钥从不发送给浏览器，也不应提交到仓库。真实模式会要求模型仅输出 `risk_level`、`summary` 和 `evidence` 的 JSON；“AI Generate Sample” 也会由模型选择受控场景模板，再由后端生成 Schema 安全的 Context。解析、超时或 Schema 问题会降级到安全陪伴输出，不会让页面崩溃。

## API

| Method | Endpoint | 用途 |
| --- | --- | --- |
| GET | `/api/demo/presets` | 获取八个演示预设 |
| GET | `/api/demo/scenario-options` | 获取可组合的用户、记忆、状态与触发选项 |
| GET | `/api/demo/scenarios/{preset_id}` | 获取包含 Context 与 Event 的完整预设 |
| POST | `/api/scenarios/generate` | 由结构化选择或受控 AI 构造版本化场景 |
| GET/POST | `/api/context` | 读取或 Schema 校验后保存 Context |
| POST | `/api/context/upload` | 导入 `.json` Context 或 `.txt/.md` 知识 |
| POST | `/api/context/generate` | 生成一个受控的样例 Context |
| POST | `/api/events/trigger` | 触发事件并运行 Agent |
| POST | `/api/agent/run` | 与 trigger 等价的编排入口 |
| GET | `/api/agent/{decision_id}` | 读取既有结构化决策 |
| GET | `/api/memory` / `/api/profile` | 读取记忆或画像 |
| POST | `/api/reset?preset_id=...` | 重置到一个预设 |

## 测试

```powershell
cd backend
python -m pytest -q

cd ../frontend
npx tsc --noEmit
npm run build
```

后端测试强制 `MOCK_MODE=true`，确保不会消耗任何真实模型 Token。

## HarmonyOS 扩展路径

1. 将 `RobotAdapter`、`WatchAdapter`、`PhoneAdapter` 换为 HarmonyOS 分布式设备/软总线实现。
2. 用 Redis 与 PostgreSQL 替换 `DemoStore`，以支持会话与长期记忆持久化。
3. 用向量数据库替换当前的 tag 检索，实现可追溯 RAG。
4. 接入可信传感器、管理员配置与授权机制，再逐步支持更多健康/家庭规则。
5. 在保留 Safety Policy 的前提下，扩展 Safety / Companion / Planning 子 Agent。
