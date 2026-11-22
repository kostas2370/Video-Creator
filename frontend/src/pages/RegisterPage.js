import React, { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { HiCheck, HiMinus } from "react-icons/hi2";
import { toast } from "react-toastify";
import { register } from "../api/apiService";
import { AuthLayout } from "../components/AuthLayout";
import { PasswordField, SubmitButton, TextField } from "../components/AuthFields";
import { useGuestRedirect } from "../hooks/useGuestRedirect";
import { useDeployment } from "../store/DeploymentContext";

export default function Register() {
  const { invite_only: inviteOnly } = useDeployment();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const submitting = useRef(false);
  const navigate = useNavigate();
  useGuestRedirect();

  const rules = [
    ["8+ characters", password.length >= 8],
    ["Upper & lowercase", /[A-Z]/.test(password) && /[a-z]/.test(password)],
    ["A number", /[0-9]/.test(password)],
    ["A special character", /[^A-Za-z0-9\s]/.test(password)],
  ];
  const passwordsMatch = password.length > 0 && password === passwordConfirm;

  async function handleRegister(event) {
    event.preventDefault();
    if (submitting.current) return;
    setError("");
    if (!username.trim() || !email.trim()) {
      setError("Enter your username and email to continue.");
      return;
    }
    if (!rules.every(([, valid]) => valid)) {
      setError("Please meet the password requirements below.");
      return;
    }
    if (!passwordsMatch) {
      setError("Your passwords don’t match yet.");
      return;
    }

    submitting.current = true;
    setLoading(true);
    try {
      const response = await register({ username, email, password });
      if (!response.ok) {
        setError(response.message || "Unable to create your account. Please try again.");
        return;
      }
      toast.success("Registered successfully, check your email for the confirmation link");
      navigate("/login/", { replace: true });
    } catch {
      setError("We couldn’t create your account. Please try again.");
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  }

  return (
    <AuthLayout register>
      <p className="auth-eyebrow">LET’S MAKE SOMETHING</p>
      <h1 id="auth-title">Create your<br />account.</h1>
      <p className="auth-subtitle">{inviteOnly ? "This beta is by invitation. Register with the email address you were invited with." : "Create your account and bring your next story to life."}</p>
      <form className="auth-form auth-register-form" onSubmit={handleRegister} aria-busy={loading}>
        <TextField
          id="username"
          label="Username"
          autoComplete="username"
          placeholder="Choose your username"
          value={username}
          onChange={event => setUsername(event.target.value)}
        />
        <TextField
          id="email"
          label="Email address"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          onChange={event => setEmail(event.target.value)}
        />
        <PasswordField
          autoComplete="new-password"
          value={password}
          onChange={event => setPassword(event.target.value)}
          aria-describedby="password-guidance"
        />
        <ul id="password-guidance" className="auth-password-rules" aria-label="Password requirements">
          {rules.map(([label, valid]) => (
            <li key={label} className={valid ? "is-valid" : ""}>
              {valid ? <HiCheck aria-hidden="true" /> : <HiMinus aria-hidden="true" />}
              <span>{label}{valid && <span className="sr-only"> — met</span>}</span>
            </li>
          ))}
        </ul>
        <PasswordField
          id="confirm_password"
          label="Confirm password"
          autoComplete="new-password"
          placeholder="Repeat your password"
          value={passwordConfirm}
          onChange={event => setPasswordConfirm(event.target.value)}
          aria-describedby={passwordConfirm ? "password-match" : undefined}
          aria-invalid={passwordConfirm ? !passwordsMatch : undefined}
        />
        {passwordConfirm && (
          <p id="password-match" className={`auth-match ${passwordsMatch ? "is-valid" : ""}`} role="status">
            {passwordsMatch ? "Passwords match. You’re all set." : "Your passwords don’t match yet."}
          </p>
        )}
        {error && <p className="auth-error" role="alert">{error}</p>}
        <SubmitButton loading={loading} pending="Creating your account…">Create your account</SubmitButton>
        <p className="auth-switch">Already have an account? <Link to="/login/">Sign in</Link></p>
      </form>
    </AuthLayout>
  );
}
