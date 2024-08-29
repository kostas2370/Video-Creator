import React  from "react";
import {
  Route,
  Routes,
  useLocation,
  useParams 
} from "react-router-dom";

import Login from "./pages/LoginPage";
import Home from "./pages/HomePage"
import Register from "./pages/RegisterPage";
import Navbar from "./components/ui/myNavBar";
import Twitch from "./pages/TwitchPage";
import { Avatar } from "./pages/AvatarPage";
import { Videos } from "./pages/VideosPage";
import useAuth from "./useAuth";
import { Video } from "./pages/VideoPage";
import { AssetPage } from "./pages/AssetPage";
function App() {

  useAuth()
  const location = useLocation();

  
  const shouldShowNavbar =
    location.pathname !== "/login/" && location.pathname !== "/register";

  return (
    <div className="">
      {shouldShowNavbar ? <Navbar /> : <></>}

      <Routes class="w-screen">
        <Route path="/login/" element={<Login />} />
        <Route path="/register/" element={<Register />} />
        <Route path="/twitch/" element={<Twitch />} />
        <Route path="/avatars/" element={<Avatar />} />
        <Route path="/videos/" element={<Videos />} />
        <Route path="/videos/:videoId/" element={<Video/>} />
        <Route path="/assets/" element={<AssetPage/>} />

        <Route path="/" element={<Home />} />
        <Route path="*" element={<>Not found</>} />

      </Routes>
    </div>
  );
}

export default App;
