import Link from "next/link";

export function SiteHeader({ lab = false }: { lab?: boolean }) {
  return <header className={`site-header ${lab ? "site-header-lab" : ""}`}>
    <div className="site-nav">
      <Link className="site-brand" href="/" aria-label="Harmony Care Agent 首页">
        <span className="site-brand-mark">H</span>
        <span><b>Harmony Care Agent</b><small>鸿蒙分布式智能陪伴</small></span>
      </Link>
      {!lab && <nav aria-label="项目导航">
        <a href="#solution">核心技术链</a>
        <a href="#requirements">命题对应</a>
        <a href="#scenarios">旗舰场景</a>
        <a href="#innovation">核心创新</a>
        <a href="#safety">安全边界</a>
      </nav>}
      <Link className="site-lab-link" href={lab ? "/" : "/lab?demo=elder-fall"}>{lab ? "返回首页" : "进入演示"}<span aria-hidden="true">↗</span></Link>
    </div>
  </header>;
}
