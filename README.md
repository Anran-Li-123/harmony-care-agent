# Harmony Care Agent Demo

《面向“一老一小”全场景看护的鸿蒙分布式智能陪伴机器人系统研发》Web Demo。

这是一个面向大学生创新竞赛的可运行演示：以 AI Agent 为家庭智能中枢，串联**环境感知 → 上下文理解 → 安全决策 → Robot / Watch / Phone 协同 → 记忆更新 → 长期画像演化**。当前的终端是 Web 模拟设备；其适配器边界已预留给未来 HarmonyOS 分布式设备实现。

## 核心设计

```text
Working / Episodic / Profile / Knowledge / Device / Sensor / Environment
                                  + New Event
                                        ↓
ContextAssembler → SafetyPolicy → KnowledgeRetriever → CareGoal / AgentPlan
                                        ↓
             PlanStep → DeviceRegistry + CapabilityMatcher → ActionRouter
                                        ↓
             Robot | Watch | Phone | Light | DoorLock | SmartScreen
                                        ↓
       FeedbackEvent → WorldState → GoalEvaluator → Follow-up Plan
                                        ↓
                  MemoryExtractor → ProfileUpdater → New Context
```

- **一套链路支持冷启动和历史用户**：新用户允许空画像、空事件记忆；每次交互仍进入统一的编排流程。
- **事件记忆不等于用户画像**：`MemoryExtractor` 写入工作/事件记忆，`ProfileUpdater` 再基于证据决定画像变化。
- **显式优先，推断克制**：称呼等显式信息可立即保存；京剧、作息等推断需要持续证据；医疗、药物、过敏、紧急联系人等高风险字段不能由一次普通事件推断。
- **安全优先于 LLM**：跌倒、儿童独处时门磁开启等明确信号先由 `SafetyPolicy` 处理，再路由终端动作。
- **能力匹配而非硬编码终端**：`DeviceRegistry` 与 `CapabilityMatcher` 按设备能力、位置、家庭成员和在线状态选择执行设备；离线设备自动跳过并使用仍可用的能力。
- **目标、计划与设备动作分层**：`CareGoal` 表达看护目标，`AgentPlan`/`PlanStep` 表达高层步骤，具体 `DeviceAction` 仍由能力匹配层生成；安全场景使用确定性计划，普通陪伴可使用现有 LLM 输出辅助高层描述。
- **受控反馈闭环**：需要确认的旗舰场景支持 `FeedbackEvent → WorldState 更新 → GoalEvaluation → Follow-up Plan → 设备执行 → Memory Finalization`；安全结果使用确定性规则，不调用 LLM。
- **闭环保持有限**：每次反馈只运行一次评估和一次 Follow-up Plan，不包含无限循环、通用自主 Replan 或真实紧急服务调用。
- **当前是可验证的 Web Mock**：六类 Harmony 设备及结构化执行结果均由 Mock Adapter 演示；`HarmonySoftBusAdapter` 仅保留接口占位，尚未接入真实 HarmonyOS SDK、软总线或硬件。
- **真正可替换**：`LLMProvider`、`DeviceAdapter`、内存 Store、Knowledge Retriever 都是清晰边界，后续可换 Redis/PostgreSQL/向量库/HarmonyOS SDK。

## 功能演示

| 预设 | 演示结果 |
| --- | --- |
| 全新老人首次交流 | 自我介绍后创建 Episode，显式学习 `preferred_name = 李爷爷` |
| 老人夜间疑似跌倒 | 卧室跌倒触发，卧室与通道灯开启，Robot 前往确认、老人 Watch 震动、Phone 通知家属 |
| 老人手表长时静止 | 请求本人和现场确认、同步监护人，但不作医疗诊断 |
| 儿童独处门磁开启 | 门磁打开，DoorLock 保持锁定，Robot 到入口提醒，SmartScreen、儿童 Watch 与 Phone 协同 |
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
    devices/        # Registry / CapabilityMatcher / Mock Adapters / ActionRouter
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
| POST | `/api/goals/{goal_id}/feedback` | 为当前 Active Goal 提交反馈并执行一次受控 Follow-up |
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

## Harmony Device Capability Layer

当前静态家庭上下文包含 `robot_01`、老人/儿童手表、监护人手机、卧室/通道灯、玄关门锁和客厅智慧屏。动作使用 `target_device_id + capability + parameters + priority + reason`，执行后返回 `DeviceExecutionResult`，旧版 `target + action` 由单一兼容层转换。UI 中的设备状态、动作和执行结果均是 Web Mock，不代表已连接真实家庭设备。

## CareGoal + Agent Plan

当前编排链路为 `Event → WorldState → Safety → CareGoal → AgentPlan → CapabilityMatcher → DeviceAction → DeviceExecutionResult`。跌倒、儿童门口、安全区和设备离线使用确定性 Planner；低风险陪伴在 Mock Mode 下仍有稳定计划。需要反馈的首轮计划停在 `AWAITING FEEDBACK`，随后可通过显式 Demo 反馈继续；系统不接入真实设备反馈。

## Feedback + Goal Evaluation

Web Demo 现在为老人跌倒和儿童门口两类旗舰场景提供显式反馈按钮。反馈必须绑定当前 `goal_id`，先更新 Context 中的当前状态并重建 WorldState，再由确定性 `GoalEvaluator` 输出 `SUCCESS`、`CONTINUE` 或 `ESCALATE`。Follow-up Plan 仍通过 CapabilityMatcher 选择在线设备，门锁只允许保持锁定。Pending Episode 使用 `related_goal_id` 原位收束为 resolved、escalated 或继续 pending，不会根据一次反馈修改长期画像。

## HarmonyOS 扩展路径

1. 在现有 `HarmonySoftBusAdapter` 边界接入真实 HarmonyOS 分布式设备/软总线实现，并替换六类 Mock Adapter。
2. 用 Redis 与 PostgreSQL 替换 `DemoStore`，以支持会话与长期记忆持久化。
3. 用向量数据库替换当前的 tag 检索，实现可追溯 RAG。
4. 接入可信传感器、管理员配置与授权机制，再逐步支持更多健康/家庭规则。
5. 在保留 Safety Policy 的前提下，扩展 Safety / Companion / Planning 子 Agent。
