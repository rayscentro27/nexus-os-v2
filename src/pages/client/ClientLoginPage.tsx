import React, { useState } from "react";
import { supabase, isSupabaseConfigured } from "../../lib/supabaseClient";
import { getPasswordResetRedirectUrl } from "../../lib/authHelpers";
import { forceAuthResetAndRedirect } from "../../lib/authSessionCleanup";
import "../../pages/goclear/goclear-public.css";

function ClientLogo() {
  return (
    <a className="gc-logo" href="/" aria-label="GoClear home">
      <span className="gc-logo-mark">✓</span>
      <span>GoClear</span>
    </a>
  );
}

export default function ClientLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(() =>
    new URLSearchParams(window.location.search).get("password-reset") === "success"
      ? "Password updated. Sign in with your new password."
      : ""
  );
  const [resetMode, setResetMode] = useState(false);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setErr("");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      const msg = error.message.toLowerCase();
      if (msg.includes("email not confirmed")) {
        setErr("Please check your email and click the confirmation link before signing in. Check your spam folder if you don't see it.");
      } else if (msg.includes("invalid login credentials")) {
        setErr("Incorrect email or password. Please try again.");
      } else {
        setErr(error.message);
      }
      setBusy(false);
    } else {
      window.location.assign("/client/dashboard");
    }
  }

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    if (!supabase) return;
    setBusy(true);
    setErr("");
    setNotice("");
    const redirectTo = getPasswordResetRedirectUrl();
    const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
    if (error) setErr(error.message);
    else setNotice("If this email is registered, a secure password-reset link has been sent. Check spam if it does not arrive.");
    setBusy(false);
  }

  return (
    <main className="gc-page gc-auth-page">
      <header className="gc-header">
        <div className="gc-container gc-header-inner">
          <ClientLogo />
        </div>
      </header>

      <section className="gc-container gc-login-card">
        <ClientLogo />
        <h1>Client Portal Login</h1>
        <p>Sign in to access your GoClear readiness dashboard.</p>

        {!isSupabaseConfigured && (
          <div className="gc-error">Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.</div>
        )}

        {resetMode ? (
          <form onSubmit={handleReset}>
            <label>
              Email Address
              <input
                placeholder="Enter your email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>
            {err && <div className="gc-error">{err}</div>}
            {notice && <div className="gc-notice">{notice}</div>}
            <button className="gc-btn gc-btn-primary gc-full-btn" type="submit" disabled={busy || !isSupabaseConfigured}>
              {busy ? "Sending…" : "Send Reset Link"}
            </button>
            <button
              className="gc-btn gc-btn-ghost gc-full-btn"
              type="button"
              onClick={() => { setResetMode(false); setErr(""); setNotice(""); }}
            >
              Back to sign in
            </button>
          </form>
        ) : (
          <form onSubmit={handleLogin}>
            <label>
              Email Address
              <input
                placeholder="Enter your email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label>
              Password
              <input
                placeholder="Enter your password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>

            {err && <div className="gc-error">{err}</div>}
            {notice && <div className="gc-notice">{notice}</div>}

            <button className="gc-btn gc-btn-primary gc-full-btn" type="submit" disabled={busy || !isSupabaseConfigured}>
              {busy ? "Signing in…" : "Sign In"}
            </button>

            <button
              className="gc-btn gc-btn-ghost gc-full-btn"
              type="button"
              onClick={() => { setResetMode(true); setErr(""); setNotice(""); }}
            >
              Need help accessing your account?
            </button>
            <button
              className="gc-btn gc-btn-ghost gc-full-btn"
              type="button"
              onClick={() => forceAuthResetAndRedirect("/client/login")}
            >
              Reset stuck session
            </button>
          </form>
        )}

        <p className="gc-secure-line">🔒 Your information is secure and encrypted.</p>
        <p style={{ fontSize: "0.85rem", color: "var(--gc-muted)", marginTop: 12, textAlign: "center" }}>
          Need help? Contact <a href="mailto:support@goclearonline.cc" style={{ color: "var(--gc-green)" }}>support@goclearonline.cc</a>
        </p>
      </section>

      <section className="gc-container gc-auth-trust-row">
        <div><strong>Secure & Private</strong><span>Bank-level encryption</span></div>
        <div><strong>Expert Support</strong><span>We're here to help</span></div>
        <div><strong>Clear Guidance</strong><span>Actionable next steps</span></div>
      </section>
    </main>
  );
}
