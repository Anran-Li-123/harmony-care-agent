# Harmony Care Agent

《面向“一老一小”全场景看护的鸿蒙分布式智能陪伴机器人系统》比赛 Web Demo。

项目以陪伴机器人作为家庭中的移动智能中枢：它理解人物、房间、设备和风险状态，建立看护目标，执行具身行动并协同全屋设备，最后依据反馈完成目标评估与事件记忆收束。

> 当前版本是可重复运行的 **Web Mock Demo**。它展示架构、交互与闭环，不表示已经接入真实 HarmonyOS 设备、软总线、机器人或传感器硬件。

## 核心技术路线

```text
Household + Static Historical Context + Current Event
                         ↓
Home World Model（家庭空间世界模型）
                         ↓
Hybrid Safety（混合安全决策）+ Care Agent（看护智能体）
                         ↓
CareGoal（看护目标）+ Agent Plan（智能行动计划）
                         ↓
Harmony Device Capability（鸿蒙设备能力）匹配与 Mock 执行
                         ↓
Embodied Execution（具身执行）+ Feedback Loop（反馈闭环）
                         ↓
Goal Evaluation（目标评估）+ Episodic Memory（事件记忆）
                         ↓
Dynamic User Profile（动态用户画像）审慎演化
```

- **Home World Model**：统一表达老人、儿童、机器人、房间、设备、传感器和风险区域。
- **Hybrid Safety**：跌倒、儿童独处门口事件等高风险场景由确定性规则优先保护；普通陪伴可以使用受控模型输出。
- **CareGoal / Agent Plan**：先定义要保护什么，再形成可解释的行动步骤；设备动作由能力层匹配，而非前端硬编码。
- **Harmony Device Capability**：机器人、灯光、门锁、智慧屏、Watch 和 Phone 均经 Mock Adapter 产生可验证执行结果；离线设备不会被选择。
- **Feedback Loop**：显式反馈会更新世界状态，触发 Goal Evaluation 和必要的 Follow-up，再收束事件记忆。

## 比赛演示模式

打开首页后选择“进入智能家庭演示”，或直接访问：

```text
http://localhost:3000/lab
```

`/lab` 默认展示两个旗舰场景。选择场景会自动加载 `family_30d_stable`、正确人物和当前事件，并重置 Runtime Goal、反馈、计划和动画状态；页面保持 **READY**，只有点击“开始场景”才运行。

### 推荐 Competition Demo Guide（约 2–3 分钟）

1. 选择 **老人夜间疑似跌倒**，点击“开始场景”。
2. 观察 Fall Event → HIGH → CareGoal → Agent Plan → 灯光 / Robot / Watch / Phone → Await Feedback。
3. 点击“老人回应：我没事”，确认 HIGH → MEDIUM、Goal COMPLETED、Memory `PENDING → RESOLVED`。
4. 保持当前家庭，选择 **儿童独处陌生敲门**，点击“开始场景”。
5. 观察 Entrance HIGH、Door `LOCKED`、Robot 前往玄关、SmartScreen / Watch / Phone 协同。
6. 点击“家长拒绝访客”，确认 Goal COMPLETED、Door 继续 `LOCKED`、Memory RESOLVED。

Advanced Experiment 默认折叠，包含家庭历史切换、自定义 Event、旧 Preset、AI 场景构造和 JSON / TXT / MD 导入；比赛演示不需要展开它。

## 两个旗舰场景

| 场景 | 闭环 |
| --- | --- |
| 老人夜间疑似跌倒 | Fall Event → HIGH → Light ON → Robot Navigate / Observe / Speak → Watch / Phone → 本人反馈 → Goal Evaluation → Episodic Memory 收束 |
| 儿童独处陌生敲门 | Door Event → Entrance HIGH → Door LOCKED → Robot 引导儿童 → SmartScreen / Watch / Phone → 家长反馈 → Goal Evaluation → Episodic Memory 收束 |

门锁在当前安全策略中只允许保持锁定，**绝不自动 unlock**。

## 当前能力与边界

| 已实现的 Web Demo 能力 | 当前未实现的真实能力 |
| --- | --- |
| Web Digital Twin、Household Context、Static Historical Context | Real HarmonyOS Device、Real Harmony SoftBus |
| Home World Model、Hybrid Safety、CareGoal、Agent Plan | Real Robot Hardware、Real Sensor Hardware |
| Mock Harmony Device Capability、Embodied Robot Simulation | ROS2 Navigation、SLAM、Vision Model |
| Feedback Closed Loop、Goal Evaluation、Memory Evolution | Medical Diagnosis、真实紧急服务调用 |

所有家庭数据与人物均为虚构。系统不构成医疗诊断、治疗建议或真实看护承诺。

## 目录结构

```text
backend/
  app/
    agent/          # World Model、安全策略、目标、计划、反馈、记忆
    devices/        # Registry、Capability Matcher、Mock Adapter、Action Router
    data/           # 静态家庭历史、Preset 与知识规则
    api/            # FastAPI endpoints
    schemas/        # Pydantic 数据契约
    services/       # DemoStore
  tests/            # Mock-only API 与核心链路测试
frontend/
  app/              # Next.js 页面与全局样式
  components/       # 首页、比赛演示、数字孪生、面板与 Pipeline
  lib/              # API client、类型、比赛场景定义
```

## 从干净环境启动

需要 Python 3.10+、Node.js 20+。

```powershell
# Terminal 1：Backend
cd backend
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2：Frontend
cd frontend
npm install
npm run dev
```

打开 `http://localhost:3000`，后端健康检查为 `http://localhost:8000/api/health`。

### Mock Mode（比赛默认）

复制根目录 `.env.example` 到 `backend/.env`，或直接创建以下最小配置：

```env
MOCK_MODE=true
MODEL_NAME=qwen3.8-flash
FRONTEND_URL=http://localhost:3000
```

Mock Mode 不需要 API Key，也不依赖外部 LLM 网络；两个旗舰 Demo、反馈闭环和自动化测试均可稳定运行。

如需试验 Real LLM Mode，可参考 `backend/.env.example` 的占位字段。真实密钥仅保存在本地 `.env`，不得提交到仓库；比赛演示不依赖此模式。

## API 概览

| Method | Endpoint | 用途 |
| --- | --- | --- |
| GET | `/api/demo/histories` | 获取静态家庭历史选项 |
| POST | `/api/demo/histories/{history_id}/load` | 加载历史并清除旧 Runtime Goal |
| POST | `/api/events/trigger` | 触发 Current Event 并执行 Care Agent |
| POST | `/api/goals/{goal_id}/feedback` | 提交当前 Goal 的显式反馈 |
| POST | `/api/context/upload` | 导入 JSON Context 或 TXT / MD 规则 |
| POST | `/api/reset?preset_id=...` | 重置到兼容 Preset |

## 验证

```powershell
cd backend
python -m pytest

cd ../frontend
npx tsc --noEmit
npm run build
```

后端测试强制使用 `MOCK_MODE=true`，不会消耗真实模型 Token。

## 未来硬件扩展

在不改变 Care Agent 核心接口的前提下，可以将 Mock Adapter 替换为经过授权的真实 HarmonyOS 分布式设备、可信传感器和机器人硬件适配器。真实环境运行还需要账户授权、隐私治理、安全测试、人工兜底与合规评估；这些不属于当前比赛 Web Demo 的实现范围。
