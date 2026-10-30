import React, { lazy, Suspense } from "react";
import { Outlet, Route, Routes, useLocation, Navigate } from "react-router-dom";

import Navbar from "./components/ui/myNavBar";
import useAuth from "./hooks/useAuth";
import PersistLogin from "./components/PersistLogin";
import useTheme from "./hooks/useTheme";
import { LegalFooter } from "./components/LegalFooter";
import { PageLoadBoundary } from "./components/PageLoadBoundary";

const ContactPage = lazy(() => import("./pages/ContactPage"));
const Login = lazy(() => import("./pages/LoginPage"));
const Home = lazy(() => import("./pages/HomePage"));
const ClipsPage = lazy(() => import("./pages/ClipsPage"));
const SeriesPage = lazy(() => import("./pages/SeriesPage"));
const CreatePage = lazy(() => import("./pages/CreatePage"));
const Register = lazy(() => import("./pages/RegisterPage"));
const ForgotPassword = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPassword = lazy(() => import("./pages/ResetPasswordPage"));
const LegalPage = lazy(() => import("./pages/LegalPage"));
const GuidePage = lazy(() => import("./pages/HelpPages").then(module => ({ default: module.GuidePage })));
const WhatsNewPage = lazy(() => import("./pages/HelpPages").then(module => ({ default: module.WhatsNewPage })));
const StoryVideo = lazy(() => import("./pages/StoryVideoPage").then(module => ({ default: module.StoryVideo })));
const Captions = lazy(() => import("./pages/CaptionsPage").then(module => ({ default: module.Captions })));
const ManualVideo = lazy(() => import("./pages/ManualVideoPage").then(module => ({ default: module.ManualVideo })));
const Avatar = lazy(() => import("./pages/AvatarPage").then(module => ({ default: module.Avatar })));
const Videos = lazy(() => import("./pages/VideosPage").then(module => ({ default: module.Videos })));
const Video = lazy(() => import("./pages/VideoPage").then(module => ({ default: module.Video })));
const AssetPage = lazy(() => import("./pages/AssetPage").then(module => ({ default: module.AssetPage })));
const ApiKeys = lazy(() => import("./pages/ApiKeysPage").then(module => ({ default: module.ApiKeys })));
const Usage = lazy(() => import("./pages/UsagePage").then(module => ({ default: module.Usage })));
const Connections = lazy(() => import("./pages/ConnectionsPage").then(module => ({ default: module.Connections })));
const Voices = lazy(() => import("./pages/VoicesPage").then(module => ({ default: module.Voices })));

function RequireAuth() {
  const { access_token } = useAuth();
  const location = useLocation();

  return access_token ? (
    <Outlet />
  ) : (
    <Navigate to="/login" state={{ from: location }} replace />
  );
}

function App() {
  const location = useLocation();
  const { access_token } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const shouldShowNavbar =
    (!!access_token || !/^\/(guide|whats-new)\/?$/.test(location.pathname)) &&
    !/^\/(privacy|terms|contact|login|register)\/?$/.test(location.pathname) &&
    !location.pathname.startsWith("/forgot-password") &&
    !location.pathname.startsWith("/reset-password");

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-white">
      {shouldShowNavbar ? (
        <Navbar theme={theme} toggleTheme={toggleTheme} />
      ) : null}

      <PageLoadBoundary key={location.pathname}>
        <Suspense fallback={<div role="status" className="flex min-h-[50vh] items-center justify-center px-6 text-sm text-gray-500 dark:text-gray-400">Loading page…</div>}>
          <Routes>
            <Route path="/guide/" element={<GuidePage />} />
            <Route path="/whats-new/" element={<WhatsNewPage />} />
            <Route path="/contact/" element={<ContactPage />} />
            <Route path="/privacy/" element={<LegalPage document="privacy" />} />
            <Route path="/terms/" element={<LegalPage document="terms" />} />
            <Route path="/" element={<PersistLogin />}>
              <Route
                path="/login/"
                element={!access_token ? <Login /> : <Navigate to="/" replace />}
              />
              <Route path="/register/" element={<Register />} />
              <Route path="/forgot-password/" element={<ForgotPassword />} />
              <Route path="/reset-password/" element={<ResetPassword />} />

              <Route element={<RequireAuth />}>
                <Route index element={<CreatePage />} />
                <Route path="/clips/" element={<ClipsPage />} />
                <Route path="/clips/:projectId/" element={<ClipsPage />} />
                <Route path="/series/" element={<SeriesPage />} />
                <Route path="/series/:seriesId/" element={<SeriesPage />} />
                <Route path="/ai/" element={<Home />} />
                <Route path="/story/" element={<StoryVideo />} />
                <Route path="/captions/" element={<Captions />} />
                <Route path="/captions/:captionId/" element={<Captions />} />
                <Route path="/manual/" element={<ManualVideo />} />
                <Route path="/avatars/" element={<Avatar />} />
                <Route path="/videos/" element={<Videos />} />
                <Route path="/videos/:videoId/" element={<Video />} />
                <Route path="/assets/" element={<AssetPage />} />
                <Route path="/api-keys/" element={<ApiKeys />} />
                <Route path="/connections/" element={<Connections />} />
                <Route path="/usage/" element={<Usage />} />
                <Route path="/voices/" element={<Voices />} />
                <Route path="*" element={<>Page not found !</>} />
              </Route>
            </Route>
          </Routes>
        </Suspense>
      </PageLoadBoundary>
      <LegalFooter />
    </div>
  );
}

export default App;
