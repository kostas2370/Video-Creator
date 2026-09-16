import React from "react";
import { Route, Routes, useLocation, Navigate } from "react-router-dom";

import Login from "./pages/LoginPage";
import Home from "./pages/HomePage";
import Register from "./pages/RegisterPage";
import Navbar from "./components/ui/myNavBar";
import Twitch from "./pages/TwitchPage";
import { Avatar } from "./pages/AvatarPage";
import { Videos } from "./pages/VideosPage";
import { Video } from "./pages/VideoPage";
import useAuth from "./hooks/useAuth";
import { AssetPage } from "./pages/AssetPage";
import { useAxiosPrivate } from "./hooks/useAxiosPrivate";
import useRefreshToken from "./hooks/useRefreshToken";
import PersistLogin from "./components/PersistLogin";
import useTheme from "./hooks/useTheme";
function App() {
  const location = useLocation();
  const { access_token } = useAuth();
  // Lives here rather than in the navbar so the theme still applies on the login and
  // register pages, where the navbar is not rendered.
  const { theme, toggleTheme } = useTheme();

  const shouldShowNavbar =
    location.pathname !== "/login/" &&
    location.pathname !== "/register" &&
    location.pathname !== "/login";

  return (
    // The shell carries the page background and default text colour. Several pages
    // render a bare fragment with no background of their own, which left them white
    // under a dark navbar; pages that set their own background still win over this.
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
          <Route
            index
            exact
            element={access_token ? <Home /> : <Navigate to="/login" replace />}
          />
          <Route path="/register/" element={<Register />} />
          <Route
            path="/twitch/"
            element={
              access_token ? <Twitch /> : <Navigate to="/login" replace />
            }
          />
          <Route
            path="/avatars/"
            element={
              access_token ? <Avatar /> : <Navigate to="/login" replace />
            }
          />
          <Route
            path="/videos/"
            element={
              access_token ? <Videos /> : <Navigate to="/login" replace />
            }
          />
          <Route
            path="/videos/:videoId/"
            element={
              access_token ? <Video /> : <Navigate to="/login" replace />
            }
          />
          <Route
            path="/assets/"
            element={
              access_token ? <AssetPage /> : <Navigate to="/login" replace />
            }
          />
          <Route
            path="*"
            element={
              access_token ? (
                <>Page not found !</>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
        </Route>
      </Routes>
    </div>
  );
}

export default App;
