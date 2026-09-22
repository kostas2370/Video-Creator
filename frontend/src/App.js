import React from "react";
import { Outlet, Route, Routes, useLocation, Navigate } from "react-router-dom";

import Login from "./pages/LoginPage";
import Home from "./pages/HomePage";
import Register from "./pages/RegisterPage";
import ForgotPassword from "./pages/ForgotPasswordPage";
import ResetPassword from "./pages/ResetPasswordPage";
import Navbar from "./components/ui/myNavBar";
import Twitch from "./pages/TwitchPage";
import { Avatar } from "./pages/AvatarPage";
import { Videos } from "./pages/VideosPage";
import { Video } from "./pages/VideoPage";
import useAuth from "./hooks/useAuth";
import { AssetPage } from "./pages/AssetPage";
import { ApiKeys } from "./pages/ApiKeysPage";
import PersistLogin from "./components/PersistLogin";
import useTheme from "./hooks/useTheme";

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
    location.pathname !== "/login/" &&
    location.pathname !== "/register" &&
    location.pathname !== "/login" &&
    !location.pathname.startsWith("/forgot-password") &&
    !location.pathname.startsWith("/reset-password");

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-900 dark:text-white">
      {shouldShowNavbar ? (
        <Navbar theme={theme} toggleTheme={toggleTheme} />
      ) : null}

      <Routes>
        <Route path="/" element={<PersistLogin />}>
          <Route
            path="/login/"
            element={!access_token ? <Login /> : <Navigate to="/" replace />}
          />
          <Route path="/register/" element={<Register />} />
          <Route path="/forgot-password/" element={<ForgotPassword />} />
          <Route path="/reset-password/" element={<ResetPassword />} />

          <Route element={<RequireAuth />}>
            <Route index element={<Home />} />
            <Route path="/twitch/" element={<Twitch />} />
            <Route path="/avatars/" element={<Avatar />} />
            <Route path="/videos/" element={<Videos />} />
            <Route path="/videos/:videoId/" element={<Video />} />
            <Route path="/assets/" element={<AssetPage />} />
            <Route path="/api-keys/" element={<ApiKeys />} />
            <Route path="*" element={<>Page not found !</>} />
          </Route>
        </Route>
      </Routes>
    </div>
  );
}

export default App;
