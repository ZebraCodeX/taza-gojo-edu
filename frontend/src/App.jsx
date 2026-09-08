// App.jsx — routing + layout. Pages are lazy-loaded so the initial shell ships
// tiny on 2G; teachers and students both share this shell.

import React, { Suspense, lazy, useEffect } from "react";
import { HashRouter, Routes, Route, NavLink, Navigate, useNavigate, useLocation } from "react-router-dom";
import { isAuthed, api } from "./api/client";
import { store, useStore } from "./store/app";
import { registerServiceWorker } from "./services/offline";

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

function RequireAuth({ children }) {
  if (!isAuthed()) return <Navigate to="/" replace />;
  return children;
}

const NAV = [
  ["/dashboard", "Learn", "🏫"],
  ["/library", "Library", "🗂"],
  ["/tutors", "Tutors", "👩🏽‍🏫"],
];

const NAV_MOBILE = [
  ["/dashboard", "Home", "🏫"],
  ["/library", "Library", "🗂"],
  ["/tutors", "Tutors", "🎥"],
  ["/profile", "Profile", "🧑🏽‍🎓"],
];

function Header() {
  const online = useStore((s) => s.online);
  const role = useStore((s) => s.user?.user?.role);
  const points = useStore((s) => s.points);
  const nav = useNavigate();

  const logout = () => {
    import("./api/client").then(({ setTokens }) => setTokens("", ""));
    location.hash = "#/";
    location.reload();
  };

  const canAdmin = role === "teacher" || role === "admin";

  return (
    <header className="site-header">
      <div className="header-row">
        <NavLink to="/dashboard" className="brand">
          <span className="brand-mark">Tz</span>
          <span className="brand-name">Taza-Gojo <b>School</b></span>
        </NavLink>
        <form
          className="header-search"
          onSubmit={(e) => {
            e.preventDefault();
            const q = e.target.elements.q.value.trim();
            if (q) nav(`/library?q=${encodeURIComponent(q)}`);
          }}
        >
          <input name="q" placeholder="Search courses, books, tutors…" aria-label="Search" />
        </form>
        <div className="header-actions">
          {points > 0 && <span className="pill brown">⚡ {points} pts</span>}
          {canAdmin && (
            <NavLink to="/admin" className={({ isActive }) => "navbtn small" + (isActive ? " on" : "")}>🛠 Admin</NavLink>
          )}
          <NavLink to="/profile" className="avatar-link" title="My profile">
            <span className="avatar">{role === "teacher" ? "👩🏽‍🏫" : "🧑🏽‍🎓"}</span>
          </NavLink>
          <button className="link" onClick={logout}>Sign out</button>
        </div>
      </div>
      <nav className="header-nav" aria-label="Main">
        {NAV.map(([to, label, icon]) => (
          <NavLink key={to} to={to} end={to === "/dashboard"} className={({ isActive }) => "navbtn" + (isActive ? " on" : "")}>
            <span className="navbtn-ico">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
        <span className={`pill ${online ? "" : "offline"}`} style={{ marginLeft: "auto" }}>
          {online ? "● Online" : "○ Offline"}
        </span>
      </nav>
    </header>
  );
}

function BottomNav() {
  const location = useLocation();
  if (isAuthed() && location.pathname.startsWith("/call/")) return null;
  return (
    <nav className="bottom-nav" aria-label="Quick">
      {NAV_MOBILE.map(([to, label, icon]) => (
        <NavLink key={to} to={to} end={to === "/dashboard"} className={({ isActive }) => "bnav" + (isActive ? " on" : "")}>
          <span className="bnav-ico">{icon}</span>
          <span className="bnav-label">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export default function App() {
  useEffect(() => {
    if (isAuthed()) {
      api
        .get("/api/v1/auth/me/")
        .then(({ data }) => {
          store.set({ user: data, points: data.points });
        })
        .catch(() => {});
    }
    registerServiceWorker();
  }, []);

  return (
    <HashRouter>
      <Suspense fallback={<div className="loading">⏳ Taza-Gojo School…</div>}>
        <Routes>
          <Route
            path="/"
            element={
              isAuthed() ? <Navigate to="/dashboard" replace /> : <LoginPage />
            }
          />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <Layout>
                  <DashboardPage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route
            path="/course/:slug"
            element={
              <RequireAuth>
                <Layout>
                  <CoursePage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route
            path="/lesson/:id"
            element={
              <RequireAuth>
                <Layout>
                  <LessonPage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route
            path="/tutors"
            element={
              <RequireAuth>
                <Layout>
                  <TutorsPage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route
            path="/call/:sessionId"
            element={
              <RequireAuth>
                <CallPage />
              </RequireAuth>
            }
          />
          <Route
            path="/library"
            element={
              <RequireAuth>
                <Layout>
                  <LibraryPage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route
            path="/library/read/:id"
            element={
              <RequireAuth>
                <Layout>
                  <ReaderPage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route
            path="/profile"
            element={
              <RequireAuth>
                <Layout>
                  <ProfilePage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireAuth>
                <Layout>
                  <AdminPage />
                </Layout>
              </RequireAuth>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </HashRouter>
  );
}

function Layout({ children }) {
  return (
    <>
      <Header />
      <main className="page">{children}</main>
      <BottomNav />
    </>
  );
}