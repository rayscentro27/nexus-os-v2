import React, { useEffect, useState } from 'react'
import { loadClientProfileIntake, saveClientProfileIntake, checkProfileIntakeComplete, type ProfileIntakeData } from '../../lib/clientPortalDataAdapter'
import { useSession } from '../../components/auth'
import { supabase, isSupabaseConfigured } from '../../lib/supabaseClient'
import { forceAuthResetAndRedirect } from '../../lib/authSessionCleanup'
import '../../pages/goclear/goclear-public.css'

const EMPTY: ProfileIntakeData = {
  legal_name: '', preferred_name: '', phone: '', mailing_address_line1: '', mailing_address_line2: '', city: '', state: '', postal_code: '',
  business_name: '', entity_type: '', ein_status: '', industry: '', naics_code: '', business_address_line1: '', business_address_line2: '',
  business_city: '', business_state: '', business_postal_code: '', time_in_business: '', monthly_revenue_range: '', funding_goal_range: '',
}

export default function ClientOnboardingPage() {
  const { user, loading: authLoading } = useSession()
  const [form, setForm] = useState<ProfileIntakeData>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (authLoading) return
    if (!user) { window.location.assign('/client/login'); return }
    let cancelled = false
    loadClientProfileIntake().then(({ data, error: loadError }) => {
      if (cancelled) return
      setForm(data)
      if (loadError) setError(loadError)
      setLoading(false)
    }).catch(() => { if (!cancelled) { setError('We could not load your setup details.'); setLoading(false) } })
    return () => { cancelled = true }
  }, [authLoading, user])

  const set = (key: keyof ProfileIntakeData) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((current) => ({ ...current, [key]: event.target.value }))

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setSaved(false)
    const completion = checkProfileIntakeComplete(form)
    if (!completion.complete) {
      setError(`Please complete: ${completion.missingFields.join(', ')}.`)
      return
    }
    setSaving(true)
    const result = await saveClientProfileIntake(form)
    setSaving(false)
    if (!result.ok) { setError(result.error || 'Your setup could not be saved.'); return }
    setSaved(true)
    window.location.assign('/client/dashboard')
  }

  if (authLoading || loading) return <main className="gc-page gc-auth-page"><section className="gc-container gc-login-card"><p>Preparing your setup…</p></section></main>
  if (!isSupabaseConfigured || !supabase) return <main className="gc-page gc-auth-page"><section className="gc-container gc-login-card"><h1>GoClear setup</h1><p>Secure account setup is unavailable until the client portal is connected.</p></section></main>

  return (
    <main className="gc-page gc-auth-page">
      <section className="gc-container gc-login-card" style={{ maxWidth: 760 }}>
        <span className="gc-pill">Step 1 of 4 · Account setup</span>
        <h1>Welcome to GoClear</h1>
        <p>Complete the short profile setup first. Then you can upload your credit report and begin your Credit &amp; Funding Readiness Review.</p>
        <form onSubmit={submit}>
          <h3>Your details</h3>
          <label>Legal name<input value={form.legal_name} onChange={set('legal_name')} required /></label>
          <label>Preferred name<input value={form.preferred_name} onChange={set('preferred_name')} /></label>
          <label>Phone<input value={form.phone} onChange={set('phone')} required /></label>
          <h3>Business details</h3>
          <label>Business name<input value={form.business_name} onChange={set('business_name')} required /></label>
          <label>Entity type<input value={form.entity_type} onChange={set('entity_type')} placeholder="LLC, sole proprietor, etc." required /></label>
          <label>Industry<input value={form.industry} onChange={set('industry')} required /></label>
          {error && <div className="gc-error" role="alert">{error}</div>}
          {saved && <div className="gc-notice" role="status">Saved.</div>}
          <button className="gc-btn gc-btn-primary gc-full-btn" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save and continue'}</button>
          <button className="gc-btn gc-btn-ghost gc-full-btn" type="button" onClick={() => forceAuthResetAndRedirect('/client/login')}>Sign out</button>
        </form>
      </section>
    </main>
  )
}
