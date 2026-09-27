import { useEffect, useState } from 'react';
import { ArrowRight, KeyRound, ShieldCheck, UserRound } from 'lucide-react';
import { usePortal } from '../../context/PortalContext';
import { supabase } from '../../../../lib/supabaseClient';

export function SettingsView() {
  const { profile, setActiveTab } = usePortal();
  const [email, setEmail] = useState('Not available');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => { supabase?.auth.getUser().then(({ data }) => setEmail(data.user?.email || 'Not available')).catch(() => {}); }, []);

  async function requestPasswordReset() {
    setMessage(''); setError('');
    if (!supabase || !email || email === 'Not available') { setError('Password reset is unavailable until your authenticated email is available.'); return; }
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, { redirectTo: `${window.location.origin}/auth/reset` });
    if (resetError) setError(resetError.message); else setMessage('Password reset instructions were requested for your account email.');
  }

  return <div className="h-full overflow-y-auto px-1 pb-8 sm:px-2">
    <div className="mb-4"><div className="text-[10px] font-bold uppercase tracking-[0.16em] text-teal-700">Account / Settings</div><h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">Settings</h1><p className="mt-1 max-w-2xl text-sm text-slate-500">Manage the account access and profile paths already supported by GoClear.</p></div>
    {(message || error) && <div role={error ? 'alert' : 'status'} className={`mb-4 rounded-lg border px-3 py-2 text-xs ${error ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-teal-200 bg-teal-50 text-teal-800'}`}>{error || message}</div>}
    <div className="max-w-3xl space-y-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"><div className="flex items-start gap-3"><div className="rounded-xl bg-teal-50 p-2 text-teal-700"><UserRound size={18} /></div><div className="flex-1"><h2 className="text-sm font-extrabold text-slate-900">Account</h2><p className="mt-1 text-xs text-slate-500">Your authenticated account identity.</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><div><div className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">Email</div><div className="mt-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800">{email}</div></div><div><div className="text-[10px] font-bold uppercase tracking-[0.08em] text-slate-500">Portal account</div><div className="mt-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800">{profile.companyName || 'Client account'}</div></div></div></div></div></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"><div className="flex items-start gap-3"><div className="rounded-xl bg-sky-50 p-2 text-sky-700"><UserRound size={18} /></div><div className="flex-1"><h2 className="text-sm font-extrabold text-slate-900">Profile</h2><p className="mt-1 text-xs text-slate-500">Update the personal and business fields supported by your existing client profile.</p><button type="button" onClick={() => setActiveTab('profile')} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 transition hover:border-teal-300 hover:text-teal-700">Open My Profile <ArrowRight size={14} /></button></div></div></section>
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5"><div className="flex items-start gap-3"><div className="rounded-xl bg-amber-50 p-2 text-amber-700"><KeyRound size={18} /></div><div className="flex-1"><h2 className="text-sm font-extrabold text-slate-900">Security</h2><p className="mt-1 text-xs leading-5 text-slate-500">Use the existing Supabase password-reset flow. GoClear does not display or store your password.</p><button type="button" onClick={requestPasswordReset} className="mt-4 rounded-lg bg-gradient-to-r from-teal-600 to-sky-600 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:from-teal-500 hover:to-sky-500">Request password reset</button></div></div></section>
      <section className="rounded-2xl border border-teal-100 bg-gradient-to-r from-teal-50 to-sky-50 p-4"><div className="flex items-start gap-3"><ShieldCheck size={18} className="mt-0.5 text-teal-700" /><div><h2 className="text-sm font-extrabold text-slate-900">Communication preferences</h2><p className="mt-1 text-xs leading-5 text-slate-600">No client-facing notification preference store is currently connected, so no preference controls are shown or implied.</p></div></div></section>
    </div>
  </div>;
}
