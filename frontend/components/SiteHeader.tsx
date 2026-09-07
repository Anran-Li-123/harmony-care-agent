import Link from "next/link";

export function SiteHeader({ lab = false }: { lab?: boolean }) {
  return <header className={`site-header ${lab ? "site-header-lab" : ""}`}>
    <div className="site-nav">
      <Link className="site-brand" href="/" aria-label="Harmony Care Agent 首页">
        <span className="site-brand-mark">H</span>
        <span><b>Harmony Care Agent</b><small>鸿蒙分布式智能陪伴</small></span>
      </Link>
      {!lab && <nav aria-label="项目导航">
        <a href="#background">项目背景</a>
        <a href="#solution">总体方案</a>
        <a href="#architecture">系统架构</a>
        <a href="#safety">安全边界</a>
        <a href="#team">团队</a>
      </nav>}
      <Link className="site-lab-link" href={lab ? "/" : "/lab"}>{lab ? "返回首页" : "进入实验室"}<span aria-hidden="true">↗</span></Link>
    </div>
  </header>;
}
