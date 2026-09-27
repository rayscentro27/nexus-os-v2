import React, { useState } from "react";
import { supabase, isSupabaseConfigured } from "../../lib/supabaseClient";
import { getPasswordResetRedirectUrl } from "../../lib/authHelpers";
import { forceAuthResetAndRedirect } from "../../lib/authSessionCleanup";

function ClientLogo() {
  return (
    <a className="inline-flex items-center gap-3 text-slate-950 no-underline" href="/" aria-label="GoClear home">
      <span className="grid h-10 w-10 place-items-center rounded-full border-[3px] border-teal-500 text-xl font-extrabold leading-none text-teal-600">✓</span>
      <span className="leading-none">
        <span className="block text-2xl font-extrabold tracking-[-0.05em]">GoClear</span>
        <span className="mt-1 block text-[9px] font-bold uppercase tracking-[0.24em] text-slate-500">ASCENT</span>
      </span>
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
      window.location.assign("/client/onboarding");
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
    <main className="min-h-screen overflow-x-hidden bg-gradient-to-br from-white via-teal-50/30 to-sky-50/50 px-5 pb-12 font-sans text-slate-900 sm:px-8">
      <header className="mx-auto flex h-20 max-w-6xl items-center justify-between">
        <div>
          <ClientLogo />
        </div>
        <a className="rounded-lg border border-slate-200 bg-white/80 px-4 py-2 text-sm font-bold text-slate-700 shadow-sm transition hover:border-teal-300 hover:text-teal-700" href="/">
          Go to GoClear
        </a>
      </header>

      <section className="mx-auto mt-10 w-full max-w-md rounded-2xl border border-slate-200/90 bg-white/95 p-6 shadow-[0_18px_50px_rgba(8,27,58,0.09)] sm:mt-14 sm:p-9">
        <div className="mb-8 text-center"><ClientLogo /></div>
        <div className="mb-7 text-center">
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-teal-700">Client Portal</p>
          <h1 className="text-3xl font-extrabold tracking-[-0.04em] text-slate-950">Client Login</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">Access your GoClear portal and continue your readiness journey.</p>
        </div>

        {!isSupabaseConfigured && (
          <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env.</div>
        )}

        {resetMode ? (
          <form className="space-y-5" onSubmit={handleReset}>
            <label className="block text-sm font-bold text-slate-800">
              <span className="mb-2 block">Email Address</span>
              <input
                className="h-12 w-full rounded-lg border border-slate-300 bg-slate-50/60 px-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/15"
                placeholder="Enter your email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>
            {err && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800" role="alert">{err}</div>}
            {notice && <div className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-800" role="status">{notice}</div>}
            <button className="h-12 w-full rounded-lg bg-teal-600 font-bold text-white shadow-sm transition hover:bg-teal-700 focus:outline-none focus:ring-4 focus:ring-teal-500/25 disabled:cursor-not-allowed disabled:opacity-60" type="submit" disabled={busy || !isSupabaseConfigured}>
              {busy ? "Sending…" : "Send Reset Link"}
            </button>
            <button
              className="h-11 w-full rounded-lg border border-slate-300 bg-white font-bold text-slate-700 transition hover:border-teal-300 hover:text-teal-700 focus:outline-none focus:ring-4 focus:ring-teal-500/15"
              type="button"
              onClick={() => { setResetMode(false); setErr(""); setNotice(""); }}
            >
              Back to sign in
            </button>
          </form>
        ) : (
          <form className="space-y-5" onSubmit={handleLogin}>
            <label className="block text-sm font-bold text-slate-800">
              <span className="mb-2 block">Email Address</span>
              <input
                className="h-12 w-full rounded-lg border border-slate-300 bg-slate-50/60 px-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/15"
                placeholder="Enter your email address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label className="block text-sm font-bold text-slate-800">
              <span className="mb-2 block">Password</span>
              <input
                className="h-12 w-full rounded-lg border border-slate-300 bg-slate-50/60 px-4 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:bg-white focus:ring-4 focus:ring-teal-500/15"
                placeholder="Enter your password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>

            {err && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800" role="alert">{err}</div>}
            {notice && <div className="rounded-lg border border-teal-200 bg-teal-50 px-3 py-2 text-sm text-teal-800" role="status">{notice}</div>}

            <button className="h-12 w-full rounded-lg bg-teal-600 font-bold text-white shadow-sm transition hover:bg-teal-700 focus:outline-none focus:ring-4 focus:ring-teal-500/25 disabled:cursor-not-allowed disabled:opacity-60" type="submit" disabled={busy || !isSupabaseConfigured}>
              {busy ? "Signing in…" : "Sign In"}
            </button>

            <button
              className="w-full text-sm font-bold text-teal-700 underline-offset-4 transition hover:text-teal-800 hover:underline focus:outline-none focus:ring-4 focus:ring-teal-500/15"
              type="button"
              onClick={() => { setResetMode(true); setErr(""); setNotice(""); }}
            >
              Forgot password?
            </button>
            <button
              className="w-full text-xs font-semibold text-slate-500 transition hover:text-teal-700 focus:outline-none focus:ring-4 focus:ring-teal-500/15"
              type="button"
              onClick={() => forceAuthResetAndRedirect("/client/login")}
            >
              Reset stuck session
            </button>
          </form>
        )}

        <p className="mt-7 text-center text-xs text-slate-500">🔒 Your information is secure and encrypted.</p>
        <p className="mt-3 text-center text-xs text-slate-500">
          Need help? Contact <a className="font-semibold text-teal-700 hover:underline" href="mailto:support@goclearonline.cc">support@goclearonline.cc</a>
        </p>
      </section>

      <section className="mx-auto mt-8 grid w-full max-w-md grid-cols-3 gap-2 text-center text-[10px] text-slate-500 sm:mt-10 sm:max-w-2xl sm:text-xs">
        <div className="rounded-lg border border-slate-200/80 bg-white/60 px-2 py-3"><strong className="block text-slate-700">Secure & Private</strong><span>Protected access</span></div>
        <div className="rounded-lg border border-slate-200/80 bg-white/60 px-2 py-3"><strong className="block text-slate-700">Expert Support</strong><span>Here to help</span></div>
        <div className="rounded-lg border border-slate-200/80 bg-white/60 px-2 py-3"><strong className="block text-slate-700">Clear Guidance</strong><span>Next steps</span></div>
      </section>
    </main>
  );
}
