import { SERVICE_OFFER_CATALOG, type ServiceOfferSlug } from '../config/serviceOfferCatalog';
import { supabase, isSupabaseConfigured } from './supabaseClient';
import { resolveClientContextForCurrentUser } from './clientAuthContext';
import { trackEvent } from './clientAnalytics';

export async function createRevenueCheckout(input: { offerSlug: ServiceOfferSlug; termsAccepted: boolean; termsVersion: string; referralCode?: string; referralSource?: string }) {
  if (!supabase || !isSupabaseConfigured) return { ok: false, error: 'payment_test_environment_not_configured' } as const;
  const { data, error } = await supabase.functions.invoke('create-stripe-checkout', { body: input });
  if (error) return { ok: false, error: 'checkout_unavailable' } as const;
  trackEvent({ event: 'revenue_checkout_started', route: '/pricing', detail: input.offerSlug });
  return { ok: true, data } as const;
}

export async function loadClientRevenueState() {
  if (!supabase || !isSupabaseConfigured) return { source: 'synthetic' as const, orders: [], fulfillments: [], packets: [], consultations: [] };
  const context = await resolveClientContextForCurrentUser();
  if (!context) return { source: 'supabase' as const, orders: [], fulfillments: [], packets: [], consultations: [] };
  const [orders, fulfillments, packets, consultations] = await Promise.all([
    supabase.from('client_orders').select('id,order_number,status,amount_cents,currency,payment_status,fulfillment_status,terms_version,paid_at,created_at,offer_id,service_offers(name,slug,tier,description)').eq('client_id', context.clientId).order('created_at', { ascending: false }),
    supabase.from('service_fulfillments').select('*').eq('client_id', context.clientId).order('updated_at', { ascending: false }),
    supabase.from('readiness_packets').select('id,order_id,version,status,approval_status,client_visible,delivered_at,created_at').eq('client_id', context.clientId).eq('client_visible', true).order('created_at', { ascending: false }),
    supabase.from('consultation_requests').select('id,order_id,entitlement_type,allowed_duration_minutes,scheduling_status,timezone,meeting_method').eq('client_id', context.clientId).order('created_at', { ascending: false }),
  ]);
  return { source: 'supabase' as const, orders: orders.data || [], fulfillments: fulfillments.data || [], packets: packets.data || [], consultations: consultations.data || [], error: orders.error?.message || fulfillments.error?.message || packets.error?.message || consultations.error?.message };
}

export function publicServiceOffers() {
  return SERVICE_OFFER_CATALOG.filter((offer) => offer.active);
}
