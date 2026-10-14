"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  ChartNoAxesCombined,
  GraduationCap,
  House,
  Settings,
  SquarePen,
} from "lucide-react";
import type { ReactNode } from "react";

const items = [
  { href: "/dashboard", label: "Hôm nay", Icon: House },
  { href: "/documents", label: "Môn học", Icon: BookOpen },
  { href: "/practice", label: "Luyện tập", Icon: SquarePen },
  { href: "/progress", label: "Tiến độ", Icon: ChartNoAxesCombined },
];
export function Navigation({ mobile = false }: { mobile?: boolean }) {
  const path = usePathname();
  return (
    <nav
      aria-label={mobile ? "Điều hướng trên điện thoại" : "Điều hướng chính"}
      className={mobile ? "bottom-nav" : "nav-list"}
    >
      {items.map(({ href, label, Icon }) => {
        const active = path === href || path.startsWith(href + "/");
        return (
          <Link
            href={href}
            key={href}
            className={`nav-item ${active ? "active" : ""}`}
            aria-current={active ? "page" : undefined}
          >
            <Icon size={20} aria-hidden="true" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
export function NavigationShell({
  children,
  username,
  logout,
}: {
  children: ReactNode;
  username: string;
  logout: ReactNode;
}) {
  return (
    <>
      <a href="#main-content" className="skip-link">
        Đến nội dung chính
      </a>
      <aside className="sidebar">
        <Link href="/dashboard" className="brand">
          <span className="brand-mark">
            <GraduationCap size={24} aria-hidden="true" />
          </span>
          <span>
            Self Study
            <br />
            Supporter
          </span>
        </Link>
        <Navigation />
        <div className="sidebar-bottom">
          <Link href="/settings" className="nav-item">
            <Settings size={20} aria-hidden="true" />
            Cài đặt
          </Link>
          {logout}
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="muted">Không gian tự học của bạn</span>
          <Link
            href="/settings"
            className="avatar"
            aria-label={`Cài đặt tài khoản ${username}`}
          >
            {username.slice(0, 1).toUpperCase()}
          </Link>
        </header>
        <main id="main-content" className="page" tabIndex={-1}>
          {children}
        </main>
      </div>
      <Navigation mobile />
    </>
  );
}
