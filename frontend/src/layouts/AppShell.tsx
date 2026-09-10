import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import type { InstitutionalRole } from "../types";

const links: Array<{ label: string; path: string; number: string; roles?: InstitutionalRole[] }> = [
  { label: "Overview", path: "/", number: "01" },
  { label: "Live map", path: "/map", number: "02" },
  { label: "Alerts", path: "/alerts", number: "03" },
  { label: "Inspections", path: "/inspections", number: "04" },
  { label: "Advisories", path: "/advisories", number: "05" },
  { label: "Dataset import", path: "/dataset-import", number: "06" },
  { label: "Model monitoring", path: "/model-monitoring", number: "07", roles: ["admin", "analyst"] },
  { label: "Data quality", path: "/data-quality", number: "08", roles: ["admin"] },
  { label: "Analytics", path: "/analytics", number: "09", roles: ["admin", "district_officer", "analyst"] },
  { label: "Operations", path: "/operations", number: "10" },
  { label: "Messaging", path: "/messaging", number: "11", roles: ["admin", "district_officer", "field_officer"] },
  { label: "User management", path: "/users", number: "12", roles: ["admin"] },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);
  const health = useQuery({
    queryKey: ["backend-health"],
    queryFn: () => api.get<{ status?: string; checks?: { database?: string } }>("/ready"),
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
  useEffect(() => {
    const updateOnlineState = () => setIsOnline(navigator.onLine);
    window.addEventListener("online", updateOnlineState);
    window.addEventListener("offline", updateOnlineState);
    return () => {
      window.removeEventListener("online", updateOnlineState);
      window.removeEventListener("offline", updateOnlineState);
    };
  }, []);
  const systemStatus = health.isPending ? "Checking system" : health.isError ? "System unavailable" : "System operational";
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">K</span><div><strong>KrishiMitra</strong><small>Crop intelligence</small></div></div>
        <div className="scope-card"><span className="eyebrow">ACTIVE SCOPE</span><strong>{user?.assigned_geography?.districts?.[0] ?? "National overview"}</strong><span>{user?.role?.replace("_", " ")}</span></div>
        <nav className="nav-list" aria-label="Primary navigation">
          {links.filter(link => !link.roles || (user?.role && link.roles.includes(user.role))).map(link => <NavLink key={link.path} to={link.path} end={link.path === "/"} className={({ isActive }) => isActive ? "nav-item active" : "nav-item"}><span className="nav-number">{link.number}</span>{link.label}</NavLink>)}
        </nav>
        <div className="sidebar-footer"><button className="nav-item muted" onClick={logout}><span className="nav-number">--</span>Sign out</button></div>
      </aside>
      <main className="main-content">
        <header className="topbar"><div><span className="eyebrow">INSTITUTIONAL CONSOLE</span><h1>Good morning, {user?.email?.split("@")[0] ?? "operator"}</h1></div><div className="topbar-actions"><span className={`live-dot ${health.isError ? "offline" : health.isPending ? "checking" : ""}`}>{systemStatus}</span><div className="avatar">{user?.email?.slice(0, 2).toUpperCase() ?? "KM"}</div></div></header>
        {!isOnline && <div className="offline-banner" role="status"><strong>You are offline.</strong><span>Read-only data may be stale, and changes will not reach the backend until connectivity returns.</span></div>}
        <Outlet />
      </main>
    </div>
  );
}
