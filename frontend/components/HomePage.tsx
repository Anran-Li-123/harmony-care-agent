import Link from "next/link";
import { SiteHeader } from "./SiteHeader";

const pipeline = ["家庭感知", "上下文汇集", "安全策略", "Agent 判断", "终端协同", "记忆演化"];
const memoryLayers = [
  ["01", "短期工作记忆", "保存当前会话正在使用的信息，并限制长度与生命周期。"],
  ["02", "时间 / 事件记忆", "记录何时、何地发生了什么，以及系统采取了哪些行动。"],
  ["03", "长期用户画像", "只从明确表达或多次一致证据中形成稳定偏好与习惯。"],
  ["04", "家庭知识规则", "承载安全规则、陪伴原则和可追溯的家庭配置。"],
];
const scenarios = [
  ["老人夜间安全", "跌倒、长时静止或终端离线时，优先请求现场确认并同步监护人。"],
  ["儿童居家看护", "门磁或手表安全区变化可以在没有对话时直接成为 Agent 输入。"],
  ["日常陪伴", "结合可靠偏好提供低打扰陪伴，不把普通需求升级为紧急事件。"],
  ["习惯长期演化", "通过连续时间记录观察作息变化，避免从一次行为推断长期画像。"],
];
const architecture = ["用户对话 / 家庭传感器", "上下文组装器", "安全策略与知识检索", "语言模型判断", "动作路由器", "机器人 / 手表 / 手机", "记忆提取与画像更新"];

export function HomePage() {
  return <div className="project-page">
    <SiteHeader />
    <main>
      <section className="project-hero">
        <div className="project-hero-grid" aria-hidden="true" />
        <div className="project-container project-hero-layout">
          <div className="project-hero-copy">
            <span className="section-kicker">大学生创新项目 · Web 演示系统</span>
            <h1>面向“一老一小”全场景看护的<br/><em>鸿蒙分布式智能陪伴</em>机器人系统</h1>
            <p>以 Agent（智能体）为家庭智能中枢，把用户记忆、环境感知、安全判断与机器人、手表、监护人手机连接为一条可观察、可复现的照护链路。</p>
            <div className="project-hero-actions"><Link className="project-primary-link" href="/lab">进入在线实验室 <span>→</span></Link><a className="project-secondary-link" href="#solution">查看系统方案</a></div>
            <ul className="project-proof-list" aria-label="项目特点"><li>支持全新与历史用户</li><li>安全规则优先</li><li>多终端协同</li><li>记忆变化可追溯</li></ul>
          </div>
          <div className="hero-system-card" aria-label="系统链路概览">
            <div className="hero-card-head"><span>家庭看护链路</span><i>实时模拟</i></div>
            <div className="hero-signal"><span>环境与传感器事件</span><svg viewBox="0 0 480 90" role="img" aria-label="动态传感器信号"><path d="M0 52 L35 44 L68 55 L99 30 L128 61 L160 42 L190 48 L222 20 L252 65 L286 39 L318 51 L350 27 L382 60 L416 38 L448 45 L480 29"/></svg></div>
            <div className="hero-pipeline">{pipeline.map((stage, index) => <div key={stage}><span>{String(index + 1).padStart(2, "0")}</span><b>{stage}</b>{index < pipeline.length - 1 && <i>→</i>}</div>)}</div>
            <div className="hero-terminal-row"><div><span className="terminal-dot cyan"/><b>机器人</b><small>现场行动</small></div><div><span className="terminal-dot violet"/><b>手表</b><small>即时触达</small></div><div><span className="terminal-dot blue"/><b>手机</b><small>监护反馈</small></div></div>
          </div>
        </div>
      </section>

      <section className="project-section" id="background"><div className="project-container"><span className="section-kicker">项目背景</span><div className="section-title-row"><h2>让分散的家庭设备形成连续、克制的看护能力</h2><p>看护并不只发生在风险出现的瞬间。系统需要理解“谁、在何处、刚刚发生了什么、过去有哪些可信记录”，再决定是否行动。</p></div><div className="problem-grid"><article><span>01</span><h3>信息分散</h3><p>对话、环境、手表与家庭传感器各自孤立，难以形成完整上下文。</p></article><article><span>02</span><h3>人因差异</h3><p>全新用户与长期陪伴用户拥有不同信息量，却需要进入同一条可靠流程。</p></article><article><span>03</span><h3>安全与打扰</h3><p>明确风险必须快速响应，普通陪伴又不应被误判为紧急事件。</p></article></div></div></section>

      <section className="project-section project-section-tint" id="solution"><div className="project-container"><span className="section-kicker">总体方案</span><div className="section-title-row"><h2>从家庭事件到设备反馈的完整闭环</h2><p>先由确定性安全策略处理明确风险，再让模型结合有限上下文与家庭规则给出结构化判断，最后路由至可用终端。</p></div><div className="solution-flow">{pipeline.map((item, index) => <article key={item}><span>{String(index + 1).padStart(2, "0")}</span><b>{item}</b><small>{["对话、手表、门磁与环境", "按需收集近期可信信息", "明确风险不依赖模型猜测", "输出风险、证据与结论", "选择仍在线的合适设备", "记录事件并审慎更新画像"][index]}</small></article>)}</div><Link className="inline-lab-card" href="/lab"><span>可运行演示</span><b>进入 `/lab` 在线实验室</b><i>组合场景并查看完整动画 →</i></Link></div></section>

      <section className="project-section memory-story" id="memory"><div className="project-container"><span className="section-kicker">上下文与记忆</span><div className="section-title-row"><h2>让“刚刚发生”与“长期了解”保持清晰边界</h2><p>事件记忆不等于用户画像。系统保留来源与可信度，避免把一次行为直接当作长期偏好，也允许完全空白的冷启动（Cold Start）。</p></div><div className="memory-layer-grid">{memoryLayers.map(([number,title,body]) => <article key={number}><span>{number}</span><div><h3>{title}</h3><p>{body}</p></div></article>)}</div></div></section>

      <section className="project-section project-section-tint" id="devices"><div className="project-container"><span className="section-kicker">鸿蒙分布式协同</span><div className="section-title-row"><h2>同一个判断，通过不同屏幕和行动抵达家庭成员</h2><p>Web 版本以模拟终端验证接口边界；未来可以把设备适配器替换为 HarmonyOS（鸿蒙操作系统）分布式设备实现。</p></div><div className="device-story-grid"><article><i>H</i><span className="current-badge">当前可模拟</span><h3>陪伴机器人</h3><p>前往指定房间、发起语音确认、提供日常陪伴并反馈执行状态。</p></article><article><i>W</i><span className="current-badge">当前可模拟</span><h3>老人 / 儿童手表</h3><p>提供佩戴、活动、安全区与在线状态，也承接震动提醒和确认操作。</p></article><article><i>P</i><span className="current-badge">当前可模拟</span><h3>监护人手机</h3><p>呈现风险级别、现场处理进度，以及当前是否需要监护人介入。</p></article><article className="future-card"><i>+</i><span className="future-badge">后续接入</span><h3>真实鸿蒙设备</h3><p>通过分布式软总线与设备 SDK 替换现有 Web 适配器，不改变 Agent 核心逻辑。</p></article></div></div></section>

      <section className="project-section" id="innovation"><div className="project-container"><span className="section-kicker">核心创新</span><div className="section-title-row"><h2>不只展示一个聊天窗口，而是展示可追踪的家庭智能系统</h2><p>项目把上下文、规则、模型、设备与记忆放进同一条可复现链路，便于评审理解系统为何行动、如何反馈。</p></div><div className="innovation-grid"><article><b>安全优先</b><p>跌倒、儿童独处门开等明确风险由确定性规则先处理。</p></article><article><b>同链路冷启动</b><p>空白用户与历史用户使用同一编排流程，只是可用证据不同。</p></article><article><b>跨终端路由</b><p>机器人、手表与手机按事件和在线状态获得不同动作。</p></article><article><b>画像审慎演化</b><p>高风险字段不由一次普通交互推断，所有变化保留来源。</p></article></div></div></section>

      <section className="project-section project-section-tint" id="scenarios"><div className="project-container"><span className="section-kicker">典型应用场景</span><div className="section-title-row"><h2>既能演示紧急事件，也能解释普通陪伴与长期变化</h2><p>实验室提供八个完整示例，并允许独立组合用户、记忆、当前状态和新事件。</p></div><div className="scenario-story-grid">{scenarios.map(([title,body],index) => <article key={title}><span>0{index+1}</span><h3>{title}</h3><p>{body}</p></article>)}</div></div></section>

      <section className="project-section architecture-section" id="architecture"><div className="project-container"><span className="section-kicker">系统架构</span><div className="section-title-row"><h2>模块边界清晰，便于从 Web 模拟逐步替换为真实能力</h2><p>语言模型、数据存储、知识检索和设备适配器均可替换；安全策略独立存在，不被模型调用结果覆盖。</p></div><div className="architecture-track">{architecture.map((item,index) => <div key={item}><span>{String(index+1).padStart(2,"0")}</span><b>{item}</b>{index<architecture.length-1 && <i>→</i>}</div>)}</div></div></section>

      <section className="project-section project-section-tint" id="capabilities"><div className="project-container"><span className="section-kicker">当前成果与能力</span><div className="capability-split"><div><h2>已经贯通的 Web 演示能力</h2><ul><li>八类完整示例与可组合场景数据</li><li>Mock（模拟）与真实模型两种运行模式</li><li>安全策略、知识检索与结构化判断</li><li>机器人、手表与手机反馈动画</li><li>工作记忆、时间记忆与画像变化展示</li><li>版本化 JSON 和知识文件导入</li></ul></div><div><h2>仍属于后续工作的能力</h2><ul className="future-list"><li>真实 HarmonyOS 分布式硬件接入</li><li>真实家庭传感器与可靠设备认证</li><li>持久化用户账户、授权与数据管理</li><li>面向真实照护的长期测试与合规验证</li><li>正式机器人外观与硬件结构设计</li></ul></div></div></div></section>

      <section className="project-section" id="safety"><div className="project-container"><span className="section-kicker">安全与隐私边界</span><div className="section-title-row"><h2>演示“如何更谨慎地判断”，而不是替代真实照护</h2><p>所有示例数据均为虚构。可穿戴状态只用于请求确认或通知监护人，系统不会根据模拟数据诊断疾病。</p></div><div className="safety-grid"><article><b>不展示隐藏推理</b><p>页面只呈现输入证据、命中规则、风险级别、行动与记忆变化。</p></article><article><b>高风险画像受限</b><p>医疗、药物、过敏与紧急联系人等字段不能由一次普通事件推断。</p></article><article><b>当前为技术演示</b><p>不构成医疗器械、诊断工具、治疗建议或真实看护承诺。</p></article></div></div></section>

      <section className="project-section project-section-tint" id="roadmap"><div className="project-container"><span className="section-kicker">后续路线</span><div className="roadmap"><article><span>当前</span><h3>可交互 Web 验证</h3><p>验证数据结构、Agent 编排、多终端路由与记忆策略。</p></article><article><span>下一阶段</span><h3>鸿蒙终端原型</h3><p>逐步替换模拟适配器，接入可信设备和受控家庭规则。</p></article><article><span>长期</span><h3>持续评估与合规</h3><p>在授权、隐私、安全测试和人工兜底下开展真实环境研究。</p></article></div></div></section>

      <section className="project-section team-section" id="team"><div className="project-container"><span className="section-kicker">项目团队</span><div className="team-placeholder"><div><span>TEAM INFORMATION</span><h2>团队信息待补充</h2><p>此区域将用于展示指导老师、项目负责人和算法、硬件、产品与 Web 方向成员。当前不使用占位姓名。</p></div><i>待补充</i></div></div></section>

      <section className="project-lab-cta"><div className="project-container"><span className="section-kicker">在线实验室</span><h2>亲自组合一次家庭事件，观察 Agent 如何判断与行动</h2><p>从完整示例、结构化组合或 AI 构造开始；没有文件也可以立即体验。</p><Link className="project-primary-link" href="/lab">打开 `/lab` 在线实验室 <span>→</span></Link></div></section>
    </main>
    <footer className="project-footer"><div className="project-container"><div><b>Harmony Care Agent</b><span>面向“一老一小”的鸿蒙分布式智能陪伴系统 Web 演示</span></div><div><Link href="/lab">在线实验室</Link><a href="#architecture">系统架构</a><a href="#safety">安全边界</a></div><p>演示数据均为虚构 · 不构成医疗诊断、治疗建议或真实看护承诺</p></div></footer>
  </div>;
}
