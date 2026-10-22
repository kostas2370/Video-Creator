import React from "react";
import { Outlet, Route, Routes, useLocation, Navigate } from "react-router-dom";

import ContactPage from "./pages/ContactPage";
import Login from "./pages/LoginPage";
import Home from "./pages/HomePage";
import CreatePage from "./pages/CreatePage";
import { StoryVideo } from "./pages/StoryVideoPage";
import { Captions } from "./pages/CaptionsPage";
import { ManualVideo } from "./pages/ManualVideoPage";
import Register from "./pages/RegisterPage";
import ForgotPassword from "./pages/ForgotPasswordPage";
import ResetPassword from "./pages/ResetPasswordPage";
import Navbar from "./components/ui/myNavBar";
import { Avatar } from "./pages/AvatarPage";
import { Videos } from "./pages/VideosPage";
import { Video } from "./pages/VideoPage";
import useAuth from "./hooks/useAuth";
import { AssetPage } from "./pages/AssetPage";
import { ApiKeys } from "./pages/ApiKeysPage";
import { Usage } from "./pages/UsagePage";
import { Connections } from "./pages/ConnectionsPage";
import { Voices } from "./pages/VoicesPage";
import PersistLogin from "./components/PersistLogin";
import useTheme from "./hooks/useTheme";
import LegalPage, { LegalFooter } from "./pages/LegalPage";

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
    !/^\/(privacy|terms|contact|login|register)\/?$/.test(location.pathname) &&
    !location.pathname.startsWith("/forgot-password") &&
    !location.pathname.startsWith("/reset-password");

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-white">
      {shouldShowNavbar ? (
        <Navbar theme={theme} toggleTheme={toggleTheme} />
      ) : null}

      <Routes>
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
      <LegalFooter />
    </div>
  );
}

export default App;
