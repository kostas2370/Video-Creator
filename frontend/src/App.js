import SearchMetadata from "./components/SearchMetadata";
import React, { lazy, Suspense } from "react";
import "./components/PublicPages.css";
import { Outlet, Route, Routes, useLocation, Navigate } from "react-router-dom";

import Navbar from "./components/ui/myNavBar";
import useAuth from "./hooks/useAuth";
import { useDeployment } from "./store/DeploymentContext";
import PersistLogin from "./components/PersistLogin";
import useTheme from "./hooks/useTheme";
import { LegalFooter } from "./components/LegalFooter";
import { PageLoadBoundary } from "./components/PageLoadBoundary";
import { VideoEditorEntry, VideoEditorLoading } from "./components/VideoEditorLoading";
import { PageLoading } from "./components/PageLoading";
import { isVideoEditorPath, pageLayout } from "./utils/pageLayout";

const RequestAccessPage = lazy(() => import("./pages/RequestAccessPage"));
const ContactPage = lazy(() => import("./pages/ContactPage"));
const SharedVideoPage = lazy(() => import("./pages/SharedVideoPage"));
const Login = lazy(() => import("./pages/LoginPage"));
const Home = lazy(() => import("./pages/HomePage"));
const ClipsPage = lazy(() => import("./pages/ClipsPage"));
const SeriesPage = lazy(() => import("./pages/SeriesPage"));
const LandingPage = lazy(() => import("./pages/LandingPage"));
const CreatePage = lazy(() => import("./pages/CreatePage"));
const Register = lazy(() => import("./pages/RegisterPage"));
const ForgotPassword = lazy(() => import("./pages/ForgotPasswordPage"));
const ResetPassword = lazy(() => import("./pages/ResetPasswordPage"));
const LegalPage = lazy(() => import("./pages/LegalPage"));
const GuidePage = lazy(() => import("./pages/GuidePage"));
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
  const { sadtalker_enabled: presentersEnabled } = useDeployment();
  const location = useLocation();
  const { access_token } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const { showNavbar, publicShell } = pageLayout(location.pathname, !!access_token);

  return (
    <div className={`min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-white ${publicShell ? "public-shell" : ""}`}>
      <SearchMetadata />
      {showNavbar ? (
        <Navbar theme={theme} toggleTheme={toggleTheme} />
      ) : null}

      <VideoEditorEntry />
      <PageLoadBoundary resetKey={location.pathname}>
        <Suspense fallback={isVideoEditorPath(location.pathname) ? <VideoEditorLoading /> : <PageLoading />}>
          <Routes>
            <Route path="/share/:token/" element={<SharedVideoPage theme={theme} toggleTheme={toggleTheme} />} />
            <Route path="/guide/" element={<GuidePage />} />
            <Route path="/whats-new/" element={<WhatsNewPage />} />
            <Route path="/request-access/" element={<RequestAccessPage theme={theme} toggleTheme={toggleTheme} />} />
            <Route path="/contact/" element={<ContactPage />} />
            <Route path="/privacy/" element={<LegalPage document="privacy" />} />
            <Route path="/terms/" element={<LegalPage document="terms" />} />
            <Route path="/" element={<PersistLogin fallback={location.pathname === "/" ? <LandingPage theme={theme} toggleTheme={toggleTheme} /> : "Loading"} />}>
              <Route index element={access_token ? <CreatePage /> : <LandingPage theme={theme} toggleTheme={toggleTheme} />} />
              <Route
                path="/login/"
                element={!access_token ? <Login /> : <Navigate to="/" replace />}
              />
              <Route path="/register/" element={<Register />} />
              <Route path="/forgot-password/" element={<ForgotPassword />} />
              <Route path="/reset-password/" element={<ResetPassword />} />

              <Route element={<RequireAuth />}>
                <Route path="/clips/" element={<ClipsPage key={location.pathname} />} />
                <Route path="/clips/:projectId/" element={<ClipsPage key={location.pathname} />} />
                <Route path="/series/" element={<SeriesPage key={location.pathname} />} />
                <Route path="/series/:seriesId/" element={<SeriesPage key={location.pathname} />} />
                <Route path="/ai/" element={<Home key="idea" />} />
                <Route path="/text/" element={<Home key="text" inputMode="text" />} />
                <Route path="/story/" element={<StoryVideo />} />
                <Route path="/captions/" element={<Captions key={location.pathname} />} />
                <Route path="/captions/:captionId/" element={<Captions key={location.pathname} />} />
                <Route path="/manual/" element={<ManualVideo />} />
                <Route path="/avatars/" element={presentersEnabled ? <Avatar /> : <Navigate to="/" replace />} />
                <Route path="/videos/" element={<Videos />} />
                <Route
                  path="/videos/:videoId/"
                  element={
                    <Suspense fallback={<VideoEditorLoading />}>
                      <Video key={location.pathname} />
                    </Suspense>
                  }
                />
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
