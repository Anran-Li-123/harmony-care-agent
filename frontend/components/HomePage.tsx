import Link from "next/link";
import { competitionSceneList } from "@/lib/competitionDemo";
import { SiteHeader } from "./SiteHeader";

const technologyChain = [
  ["多模态环境感知", "Multimodal Perception", "接收门磁、跌倒感知、Watch 与家庭环境变化。"],
  ["家庭空间世界模型", "Home World Model", "统一表达人物、机器人、房间、设备与风险区域。"],
  ["安全规则与 Agent 规划", "Hybrid Safety + AI Planning", "确定性规则保护高风险场景，Agent 建立 CareGoal 与行动计划。"],
  ["具身机器人执行", "Embodied Robot Execution", "机器人主动进入家庭空间，观察、询问并陪伴。"],
  ["鸿蒙全屋设备协同", "Harmony Distributed Capability", "发现并匹配灯光、门锁、智慧屏、Watch 与 Phone 能力。"],
  ["反馈与目标评估", "Feedback & Goal Evaluation", "依据本人或监护人反馈重新评估风险与目标。"],
  ["长期记忆与个性化", "Long-term Memory", "将闭环结果写入事件记忆，审慎演化动态用户画像。"],
];

const requirementMapping = [
  ["具身智能物理交互", "Robot Navigation / Observation / Speech", "机器人移动、现场观察与语音交互"],
  ["鸿蒙分布式能力", "Device Registry / Capability Matching / Action Routing", "全屋设备注册、能力匹配与动作路由"],
  ["一老一小", "Shared Household + Independent Memory / Profile", "共享家庭空间，各自保有独立记忆与画像"],
  ["完整闭环", "Event / Goal / Action / Feedback / Evaluation", "从事件到反馈评估的可追踪闭环"],
  ["环境感知", "Sensor + Home World Model", "把传感器变化转化为家庭空间状态"],
  ["长期陪伴", "Episodic Memory + Dynamic User Profile", "记录真实闭环结果并持续形成个性化"],
];

const innovations = [
  ["01", "具身闭环主动看护", "不是“检测 → 报警”，而是“感知 → 行动 → 反馈 → 调整”。"],
  ["02", "鸿蒙分布式能力协同", "机器人能够发现并调用全屋设备能力。"],
  ["03", "面向家庭空间的 World Model", "Agent 基于人物、机器人、房间和设备状态规划。"],
  ["04", "一老一小统一家庭智能", "同一 Household 中同时理解老人和儿童。"],
  ["05", "长期动态记忆", "从 Cold Start 到 Dynamic User Profile 持续演化。"],
  ["06", "Hybrid Safety", "高风险由确定性规则保护，普通陪伴由 LLM 提供智能与个性化。"],
];

export function HomePage() {
  return <div className="project-page">
    <SiteHeader />
    <main>
      <section className="project-hero">
        <div className="project-hero-grid" aria-hidden="true" />
        <div className="project-container project-hero-layout">
          <div className="project-hero-copy">
            <span className="section-kicker">具身智能 × 鸿蒙分布式 × 一老一小</span>
            <h1>面向“一老一小”全场景看护的<br/><em>鸿蒙分布式智能陪伴机器人系统</em></h1>
            <p>让机器人从“发现问题”走向“理解环境、主动行动、协同全屋、持续反馈”。以具身陪伴机器人为移动智能中枢，实现主动闭环看护与长期陪伴。</p>
            <div className="hero-tech-tags" aria-label="核心技术标签"><span>Embodied AI</span><span>Harmony Distributed Intelligence</span><span>Care Agent</span><span>Long-term Memory</span></div>
            <div className="project-hero-actions"><Link className="project-primary-link" href="/lab?demo=elder-fall">进入智能家庭演示 <span>→</span></Link><a className="project-secondary-link" href="#solution">查看技术方案</a></div>
            <ul className="project-proof-list"><li>机器人主动进入空间</li><li>鸿蒙全屋能力协同</li><li>老人儿童同一家庭</li><li>Event → Feedback 完整闭环</li></ul>
          </div>
          <div className="hero-system-card hero-home-card" aria-label="轻量家庭数字孪生概览">
            <div className="hero-card-head"><span>HOME INTELLIGENCE TWIN</span><i>Web Simulation</i></div>
            <div className="hero-mini-home">
              <div className="mini-room mini-living"><span>LIVING ROOM</span><b>🧒 小宇</b><i className="mini-screen">▱</i></div>
              <div className="mini-room mini-bedroom"><span>BEDROOM</span><b>👴 李爷爷</b><i className="mini-light">☼</i></div>
              <div className="mini-room mini-entrance"><span>ENTRANCE</span><i className="mini-lock">▣ LOCKED</i></div>
              <div className="mini-room mini-hallway"><span>HALLWAY</span></div>
              <div className="mini-robot"><span/><span/><b>H</b><small>EMBODIED HUB</small></div>
              <svg viewBox="0 0 600 340" aria-hidden="true"><path d="M145 112 C225 150 245 205 295 235 S395 250 470 235"/><path d="M302 234 C352 174 420 142 488 110"/></svg>
            </div>
            <div className="hero-capability-row"><span>感知</span><i>→</i><span>理解</span><i>→</i><span>行动</span><i>→</i><span>协同</span><i>→</i><span>反馈</span></div>
          </div>
        </div>
      </section>

      <section className="project-section" id="background"><div className="project-container"><span className="section-kicker">项目定位</span><div className="section-title-row"><h2>机器人不是独立设备，而是家庭中的移动智能中枢</h2><p>它连接多设备感知、家庭空间理解、安全策略、主动行动和长期记忆，让分散的全屋能力围绕一个明确的看护目标协同工作。</p></div><div className="problem-grid"><article><span>01</span><h3>主动进入现场</h3><p>风险出现后，机器人可以移动到目标空间，观察并发起确认，而不只发送消息。</p></article><article><span>02</span><h3>全屋共同响应</h3><p>灯光、门锁、智慧屏、Watch 与 Phone 按当前可用能力参与同一计划。</p></article><article><span>03</span><h3>反馈决定下一步</h3><p>系统等待真实反馈，再决定目标完成、继续等待或升级处理。</p></article></div></div></section>

      <section className="project-section project-section-tint" id="solution"><div className="project-container"><span className="section-kicker">核心技术链</span><div className="section-title-row"><h2>从家庭感知到长期陪伴的七层闭环</h2><p>每一层都有明确输入与输出；高风险判断由规则兜底，设备表现由实际执行结果驱动。</p></div><div className="solution-flow competition-tech-flow">{technologyChain.map(([title,en,body],index) => <article key={en}><span>{String(index+1).padStart(2,"0")}</span><small>{en}</small><b>{title}</b><p>{body}</p>{index<technologyChain.length-1 && <i>↓</i>}</article>)}</div></div></section>

      <section className="project-section comparison-section"><div className="project-container"><span className="section-kicker">为什么不是普通智能家居</span><div className="section-title-row"><h2>从“通知人处理”升级为“机器人带领全屋主动闭环”</h2><p>普通自动化关注单次触发；Care Agent 持续理解人物与空间，并根据反馈调整下一步行动。</p></div><div className="care-comparison"><article><span>传统方案</span><h3>传感器检测 → 手机报警 → 等人处理</h3><div className="comparison-flow"><b>传感器</b><i>→</i><b>手机</b><i>→</i><b>人工处理</b></div></article><article className="care-comparison-active"><span>本方案</span><h3>理解空间、建立目标、主动行动并持续学习</h3><div className="comparison-flow rich"><b>多设备感知</b><i>→</i><b>Home World Model</b><i>→</i><b>CareGoal</b><i>→</i><b>Robot 行动</b><i>→</i><b>全屋协同</b><i>→</i><b>反馈评估</b><i>→</i><b>长期记忆</b></div></article></div><div className="embodied-definition"><i>H</i><div><span>EMBODIED HARMONY NODE</span><b>可移动、可感知、可行动的鸿蒙具身节点</b><p>机器人负责把数字世界中的判断带入真实家庭空间，并组织周边设备共同完成 CareGoal。</p></div></div></div></section>

      <section className="project-section project-section-tint" id="requirements"><div className="project-container"><span className="section-kicker">企业命题要求 × 我们的技术实现</span><div className="section-title-row"><h2>每一项命题要求，都有可运行、可观察的实现对应</h2><p>当前交付是 Web Mock Demo，用于验证系统架构与交互闭环；不宣称已接入真实 HarmonyOS 硬件。</p></div><div className="requirement-map">{requirementMapping.map(([requirement,technology,result]) => <article key={requirement}><span>{requirement}</span><i>→</i><div><b>{technology}</b><p>{result}</p></div></article>)}</div><p className="web-mock-notice"><b>当前边界：</b>Web Simulation / Mock Device Adapter。未来可替换为真实 HarmonyOS 分布式设备实现，Agent 核心链路保持不变。</p></div></section>

      <section className="project-section flagship-section" id="scenarios"><div className="project-container"><span className="section-kicker">两个旗舰场景</span><div className="section-title-row"><h2>两条链路讲清主动看护与鸿蒙协同</h2><p>比赛演示只突出老人夜间安全和儿童独处安全，进入后自动准备 30 天稳定家庭，但不会自动运行。</p></div><div className="flagship-grid">{competitionSceneList.map((scene,index) => <article key={scene.id} className={`flagship-${scene.id}`}><span>{scene.eyebrow}</span><h3>{scene.title}</h3><p>{scene.subtitle}</p><div className="flagship-flow">{scene.flow.map((step,stepIndex) => <div key={step}><b>{step}</b>{stepIndex<scene.flow.length-1 && <i>→</i>}</div>)}</div><Link href={`/lab?demo=${scene.query}`}>进入演示 <span>0{index+1} →</span></Link></article>)}</div></div></section>

      <section className="project-section project-section-tint" id="innovation"><div className="project-container"><span className="section-kicker">核心创新</span><div className="section-title-row"><h2>先讲主动闭环，再讲分布式、空间理解与长期智能</h2><p>创新不来自功能数量，而来自机器人、全屋设备、反馈和长期上下文在同一 CareGoal 下协同。</p></div><div className="innovation-grid innovation-grid-six">{innovations.map(([number,title,body]) => <article key={number}><span>{number}</span><b>{title}</b><p>{body}</p></article>)}</div></div></section>

      <section className="project-section architecture-section" id="architecture"><div className="project-container"><span className="section-kicker">统一技术术语</span><div className="section-title-row"><h2>一套清晰语言贯穿首页与演示</h2><p>Home World Model、CareGoal、Agent Plan、Harmony Device Capability、Embodied Execution、Feedback Loop、Episodic Memory 与 Dynamic User Profile。</p></div><div className="architecture-track terminology-track">{["Home World Model","CareGoal","Agent Plan","Harmony Device Capability","Embodied Execution","Feedback Loop","Episodic Memory","Dynamic User Profile"].map((item,index) => <div key={item}><span>{String(index+1).padStart(2,"0")}</span><b>{item}</b>{index<7 && <i>→</i>}</div>)}</div></div></section>

      <section className="project-section" id="safety"><div className="project-container"><span className="section-kicker">安全与工程边界</span><div className="section-title-row"><h2>Hybrid Safety 让高风险保护不依赖模型猜测</h2><p>当前系统用于比赛技术演示，不构成医疗诊断、治疗建议或真实看护承诺。</p></div><div className="safety-grid"><article><b>确定性规则优先</b><p>跌倒和儿童独处门口事件先由安全规则建立高优先级 CareGoal。</p></article><article><b>执行结果可核验</b><p>只展示真实匹配并成功执行的设备能力，门锁不会自动解锁。</p></article><article><b>记忆审慎演化</b><p>事件记录不直接等于长期画像，所有变化保留证据来源。</p></article></div></div></section>

      <section className="project-lab-cta"><div className="project-container"><span className="section-kicker">COMPETITION DEMO</span><h2>选择一个旗舰场景，看机器人如何带领全屋完成闭环</h2><p>进入后先确认 READY，再点击“开始场景”。</p><Link className="project-primary-link" href="/lab?demo=elder-fall">进入智能家庭演示 <span>→</span></Link></div></section>
    </main>
    <footer className="project-footer"><div className="project-container"><div><b>Harmony Care Agent</b><span>面向“一老一小”的鸿蒙分布式智能陪伴机器人系统</span></div><div><Link href="/lab?demo=elder-fall">旗舰演示</Link><a href="#solution">技术链</a><a href="#safety">安全边界</a></div><p>当前为 Web Mock Demo · 演示数据均为虚构 · 不构成医疗诊断、治疗建议或真实看护承诺</p></div></footer>
  </div>;
}
