import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import reportWebVitals from "./reportWebVitals";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { BrowserRouter as Router } from "react-router-dom";
import { AuthContextProvider } from "./store/AuthContext";
import { applyTheme, initialTheme } from "./hooks/useTheme";

applyTheme(initialTheme());

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <Router>
    <AuthContextProvider>
      <App />
      <ToastContainer />
    </AuthContextProvider>


  </Router>
);

reportWebVitals();
