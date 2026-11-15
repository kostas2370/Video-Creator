import { useState } from "react";
import { HiArrowRight, HiOutlineEye, HiOutlineEyeSlash } from "react-icons/hi2";

export function TextField({ id, label, ...props }) {
  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <input id={id} name={id} required {...props} />
    </div>
  );
}

export function PasswordField({
  id = "password",
  label = "Password",
  autoComplete = "current-password",
  placeholder,
  ...props
}) {
  const [visible, setVisible] = useState(false);
  const defaultPlaceholder = autoComplete === "new-password"
    ? "Create a strong password"
    : "Enter your password";

  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <div className="auth-password">
        <input
          {...props}
          id={id}
          name={id}
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          required
          placeholder={placeholder || defaultPlaceholder}
        />
        <button
          type="button"
          aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`}
          aria-pressed={visible}
          onClick={() => setVisible(value => !value)}
        >
          {visible ? <HiOutlineEyeSlash /> : <HiOutlineEye />}
        </button>
      </div>
    </div>
  );
}

export function SubmitButton({ loading, children, pending }) {
  return (
    <button className="auth-submit" type="submit" disabled={loading}>
      {loading ? (
        <><span className="auth-spinner" aria-hidden="true" />{pending}</>
      ) : (
        <>{children}<HiArrowRight aria-hidden="true" /></>
      )}
    </button>
  );
}
