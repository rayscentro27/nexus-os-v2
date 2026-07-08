import { useState, useEffect } from 'react'
import { supabase, isSupabaseConfigured } from '../lib/supabaseClient'
import { clientPortalData } from '../data/clientPortalData'
import { clientDataMode } from '../data/clientDataMode'

export type PortalMode = 'preview' | 'live'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyRecord = Record<string, any>

export interface PortalData {
  mode: PortalMode
  liveStatus: 'demo' | 'loading' | 'connected' | 'partial' | 'error'
  loadError: string | null
  profile: AnyRecord
  readinessScores: AnyRecord
  tasks: AnyRecord[]
  creditRepair: AnyRecord
  creditProfileReadiness: AnyRecord
  businessProfileReadiness: AnyRecord
  fundingReadiness: AnyRecord
  documents: AnyRecord
  messages: AnyRecord
  businessOpportunities: AnyRecord
}

function useSupabaseClientData(userId: string) {
  const [liveData, setLiveData] = useState<Partial<PortalData>>({})
  const [status, setStatus] = useState<'loading' | 'connected' | 'partial' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isSupabaseConfigured || !clientDataMode.liveSupabaseTestClientEnabled || !userId) {
      return
    }

    let cancelled = false

    async function load() {
      try {
        const { data: membership } = await supabase!
          .from('tenant_memberships')
          .select('tenant_id, client_id')
          .eq('user_id', userId)
          .eq('role', 'client')
          .limit(1)
          .single()

        if (cancelled) return

        if (!membership?.tenant_id || !membership?.client_id) {
          setStatus('partial')
          setError('Your portal profile is being prepared. Contact support if this persists.')
          return
        }

        const [profileRes, tasksRes, scoresRes] = await Promise.all([
          supabase!.from('client_profiles').select('*').eq('tenant_id', membership.tenant_id).eq('client_id', membership.client_id).limit(1).maybeSingle(),
          supabase!.from('client_tasks').select('*').eq('tenant_id', membership.tenant_id).eq('client_id', membership.client_id).eq('client_visible', true).order('priority', { ascending: true }).limit(20),
          supabase!.from('readiness_scores').select('*').eq('tenant_id', membership.tenant_id).eq('client_id', membership.client_id).eq('client_visible', true).limit(20),
        ])

        if (cancelled) return

        const profile = profileRes.data
        const tasks = tasksRes.data ?? []
        const scores = scoresRes.data ?? []

        const readinessFromScores = (category: string) => {
          const match = scores.find((s: AnyRecord) => s.category === category)
          return match ? Number(match.score ?? 0) : 0
        }

        setLiveData({
          profile: profile ? {
            name: profile.title || profile.name || 'Client',
            membershipTier: profile.payload?.membershipTier || 'GoClear Readiness',
            currentGoal: profile.payload?.currentGoal || 'Complete your readiness checklist',
            subscriptionStatus: profile.payload?.subscriptionStatus || 'Active',
            nextReviewDate: profile.payload?.nextReviewDate || 'TBD',
            advisorName: profile.payload?.advisorName || 'GoClear Review Team',
            overallStatus: profile.status || 'onboarding',
          } : clientPortalData.clientProfile,
          readinessScores: {
            creditRepairProgress: readinessFromScores('credit_repair'),
            creditProfileReadiness: readinessFromScores('credit_profile'),
            businessProfileReadiness: readinessFromScores('business_profile'),
            fundingReadiness: readinessFromScores('funding_readiness'),
            businessOpportunityScore: readinessFromScores('business_opportunity'),
          },
          tasks: tasks.map((t: AnyRecord) => ({
            id: t.id,
            title: t.title,
            status: t.status,
            priority: t.priority,
          })),
        })
        setStatus(profile ? 'connected' : 'partial')
      } catch (e: unknown) {
        if (cancelled) return
        const msg = e instanceof Error ? e.message : 'Unable to load portal data'
        setError('Your portal data could not be loaded. Showing demo data.')
        setStatus('error')
        console.error('[ClientPortal]', msg)
      }
    }

    load()
    return () => { cancelled = true }
  }, [userId])

  return { liveData, status, error }
}

export function useClientPortalData(isPreview: boolean): PortalData {
  const [sessionUserId, setSessionUserId] = useState<string | null>(null)

  useEffect(() => {
    if (isPreview || !isSupabaseConfigured) return
    supabase?.auth.getSession().then(({ data: { session } }) => {
      setSessionUserId(session?.user?.id ?? null)
    })
    const { data: sub } = supabase?.auth.onAuthStateChange((_event, session) => {
      setSessionUserId(session?.user?.id ?? null)
    }) ?? { data: { subscription: { unsubscribe: () => {} } } }
    return () => sub.subscription.unsubscribe()
  }, [isPreview])

  const canLoadLive = !isPreview && isSupabaseConfigured && clientDataMode.liveSupabaseTestClientEnabled && sessionUserId
  const { liveData, status: liveStatus, error: loadError } = useSupabaseClientData(canLoadLive ? sessionUserId : '')

  const base: PortalData = {
    mode: isPreview ? 'preview' : 'live',
    liveStatus: 'demo',
    loadError: null,
    profile: clientPortalData.clientProfile,
    readinessScores: clientPortalData.readinessScores,
    tasks: clientPortalData.clientTasks,
    creditRepair: clientPortalData.creditRepair,
    creditProfileReadiness: clientPortalData.creditProfileReadiness,
    businessProfileReadiness: clientPortalData.businessProfileReadiness,
    fundingReadiness: clientPortalData.fundingReadiness,
    documents: clientPortalData.documents,
    messages: clientPortalData.messages,
    businessOpportunities: clientPortalData.businessOpportunities,
  }

  if (isPreview) {
    return base
  }

  if (canLoadLive && liveData.profile) {
    return {
      ...base,
      ...liveData,
      mode: 'live',
      liveStatus: liveStatus === 'loading' ? 'loading' : 'connected',
      loadError,
    }
  }

  if (canLoadLive && liveStatus === 'partial') {
    return {
      ...base,
      mode: 'live',
      liveStatus: 'partial',
      loadError: 'Your portal profile is being prepared. Contact support if this persists.',
    }
  }

  return {
    ...base,
    mode: 'live',
    liveStatus: liveStatus === 'error' ? 'error' : 'loading',
    loadError: null,
  }
}
