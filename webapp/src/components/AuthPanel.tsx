import { FormEvent, useState } from "react";

import { login, signup } from "../lib/api";
import type { UserProfile } from "../types";

type Mode = "login" | "signup";

interface Props {
  onAuthSuccess: (user: UserProfile) => void;
}

const AuthPanel = ({ onAuthSuccess }: Props) => {
  const [mode, setMode] = useState<Mode>("signup");
  const [formState, setFormState] = useState({
    name: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (field: string, value: string) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const signupPayload = { ...formState };
      const loginPayload = { email: formState.email, password: formState.password };

      const user =
        mode === "signup" ? await signup(signupPayload) : await login(loginPayload);

      onAuthSuccess(user);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Unable to complete request.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: 420, width: "100%" }}>
      <h2 style={{ marginTop: 0 }}>
        {mode === "signup" ? "Create your study locker" : "Jump back in"}
      </h2>
      <p style={{ marginTop: 4, color: "#475569" }}>
        Store your topics, quizzes, and audio plans securely via Redis.
      </p>
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: 16 }}>
        {mode === "signup" && (
          <input
            type="text"
            placeholder="Full name"
            value={formState.name}
            onChange={(e) => handleChange("name", e.target.value)}
            required
          />
        )}
        <input
          type="email"
          placeholder="Email address"
          value={formState.email}
          onChange={(e) => handleChange("email", e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={formState.password}
          onChange={(e) => handleChange("password", e.target.value)}
          required
        />
        {mode === "signup" && (
          <input
            type="password"
            placeholder="Confirm password"
            value={formState.confirm_password}
            onChange={(e) => handleChange("confirm_password", e.target.value)}
            required
          />
        )}
        {error && (
          <div style={{ color: "#dc2626", fontSize: "0.9rem" }}>{error}</div>
        )}
        <button className="primary" type="submit" disabled={loading}>
          {loading ? "Working..." : mode === "signup" ? "Create account" : "Login"}
        </button>
      </form>
      <p style={{ marginTop: 16, fontSize: "0.9rem" }}>
        {mode === "signup" ? "Already registered? " : "Need an account? "}
        <button
          type="button"
          className="secondary"
          onClick={() => setMode(mode === "signup" ? "login" : "signup")}
          style={{ padding: "0.35rem 0.75rem", marginLeft: 8 }}
        >
          {mode === "signup" ? "Log in" : "Sign up"}
        </button>
      </p>
    </div>
  );
};

export default AuthPanel;

