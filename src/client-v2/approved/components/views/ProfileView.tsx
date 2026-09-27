import React, { useEffect, useMemo, useState } from 'react';
import { Check, CircleUserRound, LockKeyhole, Save, ShieldCheck } from 'lucide-react';
import { usePortal } from '../../context/PortalContext';
import { loadClientProfileIntake, saveClientProfileIntake, checkProfileIntakeComplete, type ProfileIntakeData } from '../../../../lib/clientPortalDataAdapter';
import { supabase } from '../../../../lib/supabaseClient';

const inputClass = 'mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-teal-500 focus:bg-white focus:ring-2 focus:ring-teal-500/20';
const labelClass = 'text-[11px] font-bold uppercase tracking-[0.08em] text-slate-500';

function Field({ label, value, onChange, disabled = false, placeholder = '' }: { label: string; value: string; onChange?: (value: string) => void; disabled?: boolean; placeholder?: string }) {
  return <label className="block">
    <span className={labelClass}>{label}</span>
    <input className={`${inputClass} ${disabled ? 'cursor-not-allowed bg-slate-100 text-slate-500' : ''}`} value={value} disabled={disabled} placeholder={placeholder} onChange={(event) => onChange?.(event.target.value)} />
  </label>;
}

function Section({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
    <div className="mb-4 flex items-start justify-between gap-4">
      <div><h2 className="text-sm font-extrabold text-slate-900">{title}</h2><p className="mt-1 text-xs leading-5 text-slate-500">{description}</p></div>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">{children}</div>
  </section>;
}

export function ProfileView() {
  const { profile } = usePortal();
  const [form, setForm] = useState<ProfileIntakeData | null>(null);
  const [email, setEmail] = useState('Not available');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([
      loadClientProfileIntake(),
      supabase?.auth.getUser().catch(() => ({ data: { user: null } })) || Promise.resolve({ data: { user: null } }),
    ]).then(([result, auth]) => {
      if (!active) return;
      setForm(result.data);
      setEmail(auth.data.user?.email || 'Not available');
      setError(result.error || '');
      setLoading(false);
    }).catch(() => { if (active) { setError('Profile could not be loaded.'); setLoading(false); } });
    return () => { active = false; };
  }, []);

  const completion = useMemo(() => form ? checkProfileIntakeComplete(form) : { percent: 0, missingFields: [], complete: false }, [form]);
  const update = (key: keyof ProfileIntakeData, value: string) => setForm((current) => current ? { ...current, [key]: value } : current);

  async function save() {
    if (!form) return;
    setSaving(true); setMessage(''); setError('');
    const result = await saveClientProfileIntake(form);
    setSaving(false);
    if (!result.ok) setError(result.error || 'Profile could not be saved.');
    else setMessage('Profile saved securely.');
  }

  if (loading || !form) return <div className="flex h-full items-center justify-center text-sm text-slate-500">Loading your profile…</div>;

  return <div className="h-full overflow-y-auto px-1 pb-8 sm:px-2">
    <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
      <div><div className="text-[10px] font-bold uppercase tracking-[0.16em] text-teal-700">Account / My Profile</div><h1 className="mt-1 text-2xl font-black tracking-tight text-slate-900">Your profile</h1><p className="mt-1 max-w-2xl text-sm text-slate-500">Keep your identity and business foundation current for your GoClear readiness journey.</p></div>
      <button type="button" onClick={save} disabled={saving} className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-teal-600 to-sky-600 px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:from-teal-500 hover:to-sky-500 disabled:cursor-wait disabled:opacity-60"><Save size={14} />{saving ? 'Saving…' : 'Save profile'}</button>
    </div>
    {(message || error) && <div role={error ? 'alert' : 'status'} className={`mb-4 rounded-lg border px-3 py-2 text-xs ${error ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-teal-200 bg-teal-50 text-teal-800'}`}>{error || message}</div>}
    <div className="grid gap-4 xl:grid-cols-[250px_minmax(0,1fr)]">
      <aside className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col items-center text-center">
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-teal-100 to-sky-100 text-teal-700 ring-4 ring-teal-500/10"><CircleUserRound size={46} strokeWidth={1.4} /></div>
          <h2 className="mt-3 text-base font-extrabold text-slate-900">{profile.name || form.preferred_name || form.legal_name || 'Client account'}</h2>
          <p className="mt-1 text-xs text-slate-500">{form.business_name || profile.companyName || 'Business profile'}</p>
          <div className="mt-4 w-full rounded-xl border border-slate-100 bg-slate-50 p-3 text-left"><div className="flex items-center justify-between"><span className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-500">Profile completeness</span><span className="text-lg font-black text-teal-700">{completion.percent}%</span></div><div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-gradient-to-r from-teal-500 to-sky-500" style={{ width: `${completion.percent}%` }} /></div>{completion.missingFields.length > 0 && <p className="mt-2 text-[11px] leading-4 text-slate-500">Missing: {completion.missingFields.slice(0, 3).join(', ')}{completion.missingFields.length > 3 ? '…' : ''}</p>}{completion.complete && <p className="mt-2 flex items-center gap-1 text-[11px] font-semibold text-teal-700"><Check size={13} /> Core profile complete</p>}</div>
          <div className="mt-4 w-full rounded-xl border border-dashed border-slate-200 p-3 text-left"><div className="flex items-center gap-2 text-xs font-bold text-slate-700"><LockKeyhole size={14} className="text-slate-400" />Profile photo</div><p className="mt-1 text-[11px] leading-4 text-slate-500">Photo upload is unavailable because the existing private storage contract is document-only.</p></div>
          <div className="mt-3 w-full rounded-xl border border-dashed border-slate-200 p-3 text-left"><div className="flex items-center gap-2 text-xs font-bold text-slate-700"><LockKeyhole size={14} className="text-slate-400" />Business logo</div><p className="mt-1 text-[11px] leading-4 text-slate-500">Logo upload is not connected to an approved client storage field.</p></div>
        </div>
      </aside>
      <div className="space-y-4">
        <Section title="Personal information" description="Use the name and contact details GoClear should use for your account record.">
          <Field label="Legal name" value={form.legal_name} onChange={(value) => update('legal_name', value)} />
          <Field label="Preferred name" value={form.preferred_name} onChange={(value) => update('preferred_name', value)} placeholder="Optional" />
          <Field label="Account email" value={email} disabled />
          <Field label="Phone" value={form.phone} onChange={(value) => update('phone', value)} />
          <Field label="Mailing address" value={form.mailing_address_line1} onChange={(value) => update('mailing_address_line1', value)} />
          <Field label="Address line 2" value={form.mailing_address_line2} onChange={(value) => update('mailing_address_line2', value)} placeholder="Optional" />
          <Field label="City" value={form.city} onChange={(value) => update('city', value)} />
          <Field label="State" value={form.state} onChange={(value) => update('state', value)} />
          <Field label="ZIP code" value={form.postal_code} onChange={(value) => update('postal_code', value)} />
        </Section>
        <Section title="Business information" description="These fields already exist in the client profile intake contract and are saved to your tenant-scoped profile.">
          <Field label="Business name" value={form.business_name} onChange={(value) => update('business_name', value)} />
          <Field label="Entity type" value={form.entity_type} onChange={(value) => update('entity_type', value)} />
          <Field label="State of formation" value={form.business_state} onChange={(value) => update('business_state', value)} />
          <Field label="Industry" value={form.industry} onChange={(value) => update('industry', value)} />
          <Field label="NAICS code" value={form.naics_code} onChange={(value) => update('naics_code', value)} placeholder="Optional" />
          <Field label="EIN status" value={form.ein_status} onChange={(value) => update('ein_status', value)} placeholder="Status only — never enter a full EIN" />
          <Field label="Business address" value={form.business_address_line1} onChange={(value) => update('business_address_line1', value)} />
          <Field label="Business city" value={form.business_city} onChange={(value) => update('business_city', value)} />
          <Field label="Business state" value={form.business_state} onChange={(value) => update('business_state', value)} />
          <Field label="Business ZIP code" value={form.business_postal_code} onChange={(value) => update('business_postal_code', value)} />
        </Section>
        <div className="rounded-2xl border border-teal-100 bg-gradient-to-r from-teal-50 to-sky-50 p-4"><div className="flex items-start gap-3"><ShieldCheck size={18} className="mt-0.5 text-teal-700" /><div><h2 className="text-sm font-extrabold text-slate-900">Profile data boundary</h2><p className="mt-1 text-xs leading-5 text-slate-600">Profile completeness is informational only. It does not change your credit or funding-readiness scores. Sensitive financial and identity documents stay in their existing governed workflows.</p></div></div></div>
      </div>
    </div>
  </div>;
}
