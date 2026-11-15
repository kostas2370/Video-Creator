import React, { useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-toastify";
import { login } from "../api/apiService";
import { AuthLayout } from "../components/AuthLayout";
import { PasswordField, SubmitButton, TextField } from "../components/AuthFields";
import useAuth from "../hooks/useAuth";
import { useGuestRedirect } from "../hooks/useGuestRedirect";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  const { setAccessToken, setCSRFToken } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const fromLocation = location?.state?.from?.pathname || "/";
  useGuestRedirect();

  async function handleLogin(event) {
    event.preventDefault();
    if (submitting.current) return;
    setError("");
    if (!username.trim() || !password.trim()) {
      setError("Enter your username and password to continue.");
      return;
    }

    submitting.current = true;
    setLoading(true);
    try {
      const response = await login({ username, password, remember_me: rememberMe });
      if (!response.ok) {
        setError(response.message || "Unable to sign in. Please try again.");
        return;
      }
      setAccessToken(response.data.tokens.access);
      setCSRFToken(response.headers["x-csrftoken"]);
      toast.success("Login successful");
      navigate(fromLocation, { replace: true });
    } catch {
      setError("We couldn’t sign you in. Please try again.");
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <p className="auth-eyebrow">WELCOME BACK</p>
      <h1 id="auth-title">Pick up your next<br />great idea.</h1>
      <p className="auth-subtitle">Sign in to your Viddie creative space.</p>
      <form onSubmit={handleLogin} className="auth-form" aria-busy={loading}>
        <TextField
          id="username"
          label="Username"
          autoComplete="username"
          placeholder="Enter your username"
          value={username}
          onChange={event => setUsername(event.target.value)}
        />
        <PasswordField value={password} onChange={event => setPassword(event.target.value)} />
        <div className="auth-options">
          <label>
            <input
              type="checkbox"
              checked={rememberMe}
              onChange={event => setRememberMe(event.target.checked)}
            />
            Remember me
          </label>
          <Link to="/forgot-password/">Forgot password?</Link>
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <SubmitButton loading={loading} pending="Signing in…">Sign in</SubmitButton>
        <p className="auth-switch">
          Don’t have an account? <Link to="/register/">Create an account</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
