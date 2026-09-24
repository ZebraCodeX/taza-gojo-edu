// App.jsx — routing + app shell.
//
// Desktop: fixed sidebar with grouped navigation + topbar (search, theme,
// language, account). Mobile: topbar + thumb-friendly bottom tabs, with a
// "More" sheet for the rest. Pages are lazy-loaded so the shell ships tiny.

import React, { Suspense, lazy, useEffect, useState } from "react";
import { HashRouter, Routes, Route, NavLink, Navigate, useNavigate, useLocation } from "react-router-dom";
import { isAuthed, api } from "./api/client";
import { store, useStore } from "./store/app";
import { registerServiceWorker } from "./services/offline";
import { useI18n } from "./i18n";
import LanguageSwitcher from "./components/LanguageSwitcher";
import ThemeToggle from "./components/ThemeToggle";

const LoginPage = lazy(() => import("./pages/LoginPage"));
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const CoursePage = lazy(() => import("./pages/CoursePage"));
const LessonPage = lazy(() => import("./pages/LessonPage"));
const TutorsPage = lazy(() => import("./pages/TutorsPage"));
const CallPage = lazy(() => import("./pages/CallPage"));
const LibraryPage = lazy(() => import("./pages/LibraryPage"));
const ReaderPage = lazy(() => import("./pages/ReaderPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const AssessmentsPage = lazy(() => import("./pages/AssessmentsPage"));
const AssessmentRunnerPage = lazy(() => import("./pages/AssessmentRunnerPage"));
const LabsPage = lazy(() => import("./pages/LabsPage"));
const LabRunnerPage = lazy(() => import("./pages/LabRunnerPage"));
const LivePage = lazy(() => import("./pages/LivePage"));
const CertificatesPage = lazy(() => import("./pages/CertificatesPage"));
const ProgressPage = lazy(() => import("./pages/ProgressPage"));
const TeacherPage = lazy(() => import("./pages/TeacherPage"));

function RequireAuth({ children }) {
  if (!isAuthed()) return <Navigate to="/" replace />;
  return children;
}

const NAV_GROUPS = [
  {
    title: "Learn",
    items: [
      { to: "/dashboard", key: "home", icon: "🏠" },
      { to: "/library", key: "library", icon: "📚" },
    ],
  },
  {
    title: "Practice",
    items: [
      { to: "/assessments", key: "assessments", icon: "📝" },
      { to: "/labs", key: "labs", icon: "🧪" },
    ],
  },
  {
    title: "Connect",
    items: [
      { to: "/live", key: "live", icon: "🎥" },
      { to: "/tutors", key: "tutors", icon: "👩🏽‍🏫" },
    ],
  },
  {
    title: "You",
    items: [
      { to: "/progress", key: "progress", icon: "📈" },
      { to: "/certificates", key: "certificates", icon: "🏅" },
      { to: "/profile", key: "profile", icon: "🧑🏽‍🎓" },
    ],
  },
];

const MOBILE_TABS = [
  ["/dashboard", "home", "🏠"],
  ["/assessments", "assessments", "📝"],
  ["/labs", "labs", "🧪"],
  ["/live", "live", "🎥"],
];

const MORE_LINKS = [
  ["/library", "library", "📚"],
  ["/tutors", "tutors", "👩🏽‍🏫"],
  ["/progress", "progress", "📈"],
  ["/certificates", "certificates", "🏅"],
  ["/profile", "profile", "🧑🏽‍🎓"],
];

function Sidebar({ role }) {
  const { t } = useI18n();
  const user = useStore((s) => s.user);
  const canAdmin = role === "teacher" || role === "admin";
  return (
    <aside className="sidebar">
      <NavLink to="/dashboard" className="sidebar-brand">
        <span className="brand-mark">Tz</span>
        <span className="brand-name">Taza-Gojo <b>School</b></span>
      </NavLink>
      <nav className="sidebar-nav" aria-label="Main">
        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <div className="nav-group-title">{group.title}</div>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/dashboard"}
                className={({ isActive }) => "snav" + (isActive ? " on" : "")}
              >
                <span className="snav-ico">{item.icon}</span>
                <span>{t(item.key)}</span>
              </NavLink>
            ))}
          </div>
        ))}
        {canAdmin && (
          <div>
            <div className="nav-group-title">Manage</div>
            <NavLink to="/teacher" className={({ isActive }) => "snav" + (isActive ? " on" : "")}>
              <span className="snav-ico">👩🏽‍🏫</span>
              <span>Teacher console</span>
            </NavLink>
            <NavLink to="/admin" className={({ isActive }) => "snav" + (isActive ? " on" : "")}>
              <span className="snav-ico">🛠</span>
              <span>{t("admin")}</span>
            </NavLink>
          </div>
        )}
      </nav>
      <div className="sidebar-foot">
        <NavLink to="/profile" className="user-card">
          <span className="avatar">{role === "teacher" ? "👩🏽‍🏫" : "🧑🏽‍🎓"}</span>
          <span>
            <span className="u-name">{user?.user?.username || "learner"}</span>
            <span className="u-role">{role || "student"}</span>
          </span>
        </NavLink>
      </div>
    </aside>
  );
}

function Topbar({ role }) {
  const { t } = useI18n();
  const online = useStore((s) => s.online);
  const points = useStore((s) => s.points);
  const nav = useNavigate();
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <NavLink to="/dashboard" className="brand">
          <span className="brand-mark" style={{ width: 32, height: 32, fontSize: 13, borderRadius: 9 }}>Tz</span>
          <span className="brand-name" style={{ fontSize: 15 }}>Taza-Gojo</span>
        </NavLink>
        <form
          className="topbar-search"
          onSubmit={(e) => {
            e.preventDefault();
            const q = e.target.elements.q.value.trim();
            if (q) nav(`/library?q=${encodeURIComponent(q)}`);
          }}
        >
          <input name="q" placeholder="Search courses, books, labs…" aria-label="Search" />
        </form>
        <div className="topbar-actions">
          {points > 0 && <span className="pill brown">⚡ {points}</span>}
          <span className={`pill ${online ? "" : "offline"}`}>{online ? t("online") : t("offline")}</span>
          <LanguageSwitcher />
          <ThemeToggle />
          <NavLink to="/profile" className="avatar-link" title="My profile">
            <span className="avatar">{role === "teacher" ? "👩🏽‍🏫" : "🧑🏽‍🎓"}</span>
          </NavLink>
        </div>
      </div>
    </header>
  );
}

function BottomNav() {
  const { t } = useI18n();
  const role = useStore((s) => s.user?.user?.role);
  const location = useLocation();
  const [sheet, setSheet] = useState(false);
  if (isAuthed() && location.pathname.startsWith("/call/")) return null;
  const more = (role === "teacher" || role === "admin")
    ? [...MORE_LINKS, ["/teacher", "Teacher console", "👩🏽‍🏫"]]
    : MORE_LINKS;

  const logout = () => {
    import("./api/client").then(({ setTokens }) => setTokens("", ""));
    location.hash = "#/";
    location.reload();
  };

  return (
    <>
      <nav className="bottom-nav" aria-label="Quick">
        {MOBILE_TABS.map(([to, key, icon]) => (
          <NavLink key={to} to={to} end={to === "/dashboard"} className={({ isActive }) => "bnav" + (isActive ? " on" : "")}>
            <span className="bnav-ico">{icon}</span>
            <span className="bnav-label">{t(key)}</span>
          </NavLink>
        ))}
        <button className="bnav" onClick={() => setSheet(true)}>
          <span className="bnav-ico">⋯</span>
          <span className="bnav-label">More</span>
        </button>
      </nav>
      {sheet && (
        <div className="sheet-scrim" onClick={() => setSheet(false)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <div className="sheet-handle" />
            <div className="sheet-grid">
              {more.map(([to, key, icon]) => (
                <NavLink key={to} to={to} className="sheet-item" onClick={() => setSheet(false)}>
                  <span className="si-ico">{icon}</span>
                  {t(key)}
                </NavLink>
              ))}
              <button className="sheet-item" onClick={logout}>
                <span className="si-ico">🚪</span>
                {t("signOut")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function App() {
  const role = useStore((s) => s.user?.user?.role);
  useEffect(() => {
    if (isAuthed()) {
      api.get("/api/v1/auth/me/").then(({ data }) => store.set({ user: data, points: data.points })).catch(() => {});
    }
    registerServiceWorker();
  }, []);

  return (
    <HashRouter>
      <Suspense fallback={<div className="loading">⏳ Taza-Gojo School…</div>}>
        <Routes>
          <Route path="/" element={isAuthed() ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
          <Route path="/dashboard" element={<RequireAuth><Layout role={role}><DashboardPage /></Layout></RequireAuth>} />
          <Route path="/course/:slug" element={<RequireAuth><Layout role={role}><CoursePage /></Layout></RequireAuth>} />
          <Route path="/lesson/:id" element={<RequireAuth><Layout role={role}><LessonPage /></Layout></RequireAuth>} />
          <Route path="/assessments" element={<RequireAuth><Layout role={role}><AssessmentsPage /></Layout></RequireAuth>} />
          <Route path="/assessment/:slug" element={<RequireAuth><Layout role={role}><AssessmentRunnerPage /></Layout></RequireAuth>} />
          <Route path="/labs" element={<RequireAuth><Layout role={role}><LabsPage /></Layout></RequireAuth>} />
          <Route path="/lab/:slug" element={<RequireAuth><Layout role={role}><LabRunnerPage /></Layout></RequireAuth>} />
          <Route path="/live" element={<RequireAuth><Layout role={role}><LivePage /></Layout></RequireAuth>} />
          <Route path="/certificates" element={<RequireAuth><Layout role={role}><CertificatesPage /></Layout></RequireAuth>} />
          <Route path="/progress" element={<RequireAuth><Layout role={role}><ProgressPage /></Layout></RequireAuth>} />
          <Route path="/teacher" element={<RequireAuth><Layout role={role}><TeacherPage /></Layout></RequireAuth>} />
          <Route path="/tutors" element={<RequireAuth><Layout role={role}><TutorsPage /></Layout></RequireAuth>} />
          <Route path="/call/:sessionId" element={<RequireAuth><CallPage /></RequireAuth>} />
          <Route path="/library" element={<RequireAuth><Layout role={role}><LibraryPage /></Layout></RequireAuth>} />
          <Route path="/library/read/:id" element={<RequireAuth><Layout role={role}><ReaderPage /></Layout></RequireAuth>} />
          <Route path="/profile" element={<RequireAuth><Layout role={role}><ProfilePage /></Layout></RequireAuth>} />
          <Route path="/admin" element={<RequireAuth><Layout role={role}><AdminPage /></Layout></RequireAuth>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </HashRouter>
  );
}

function Layout({ children, role }) {
  return (
    <div className="app-shell">
      <Sidebar role={role} />
      <div className="app-main">
        <Topbar role={role} />
        <main className="page">{children}</main>
      </div>
      <BottomNav />
    </div>
  );
}
