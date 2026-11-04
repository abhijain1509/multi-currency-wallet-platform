import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setSession } from "../api/client.js";
import { CURRENCIES } from "../lib/money.js";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    default_currency: "USD",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    if (submitting) return;
    setError("");
    setSubmitting(true);
    try {
      const fn = mode === "login" ? api.login : api.signup;
      const payload =
        mode === "login"
          ? { email: form.email, password: form.password }
          : form;
      const res = await fn(payload);
      setSession(res.user);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="card" style={{ maxWidth: 420, margin: "48px auto" }}>
      <h2>{mode === "login" ? "Log in" : "Create account"}</h2>
      <form onSubmit={submit} className="field" style={{ gap: 12 }}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={update("email")}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={form.password}
            onChange={update("password")}
            minLength={8}
            required
          />
        </div>
        {mode === "signup" && (
          <>
            <div className="field">
              <label htmlFor="full_name">Full name</label>
              <input
                id="full_name"
                value={form.full_name}
                onChange={update("full_name")}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="default_currency">Default currency</label>
              <select
                id="default_currency"
                value={form.default_currency}
                onChange={update("default_currency")}
              >
                {CURRENCIES.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </div>
          </>
        )}
        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        <button type="submit" disabled={submitting}>
          {submitting ? "Please wait\u2026" : mode === "login" ? "Log in" : "Sign up"}
        </button>
      </form>
      <p style={{ marginTop: 16 }}>
        {mode === "login" ? "No account?" : "Have an account?"}{" "}
        <button
          type="button"
          className="linklike"
          onClick={() => {
            setMode(mode === "login" ? "signup" : "login");
            setError("");
          }}
        >
          {mode === "login" ? "Sign up" : "Log in"}
        </button>
      </p>
    </div>
  );
}
