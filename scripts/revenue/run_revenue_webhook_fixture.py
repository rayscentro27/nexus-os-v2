#!/usr/bin/env python3
"""Send a signed Stripe-shaped test event through the real webhook boundary.

This utility never writes client_orders directly and never accepts live Stripe
secrets. It is for local/sandbox certification only.
"""
from __future__ import annotations
import argparse, hashlib, hmac, json, os, time, urllib.request
from revenue_common import print_json, settings

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--event', choices=['checkout.session.completed','payment_intent.succeeded','payment_intent.payment_failed','checkout.session.expired','charge.refunded','charge.dispute.created'], required=True); parser.add_argument('--order-id', required=True); parser.add_argument('--dry-run', action='store_true'); args = parser.parse_args()
    env = settings(); secret = env.get('STRIPE_WEBHOOK_SECRET', ''); base = env.get('VITE_SUPABASE_URL', '')
    event_id = 'evt_synthetic_' + hashlib.sha256(f'{args.event}:{args.order_id}'.encode()).hexdigest()[:24]
    object_id = 'cs_synthetic_' + hashlib.sha256(args.order_id.encode()).hexdigest()[:20]
    payload = {'id': event_id, 'object': 'event', 'created': int(time.time()), 'type': args.event, 'data': {'object': {'id': object_id, 'object': 'checkout.session' if args.event.startswith('checkout') else 'payment_intent', 'payment_status': 'paid' if args.event in {'checkout.session.completed','payment_intent.succeeded'} else 'unpaid', 'payment_intent': 'pi_synthetic_' + hashlib.sha256(args.order_id.encode()).hexdigest()[:20], 'client_reference_id': args.order_id, 'metadata': {'order_id': args.order_id, 'synthetic': 'true'}}}}
    raw = json.dumps(payload, separators=(',', ':')); result = {'event_type': args.event, 'event_id': event_id, 'order_id_present': True, 'signed': bool(secret), 'live_mode': False, 'direct_paid_write': False}
    if args.dry_run: print_json(result); return
    if not secret or not secret.startswith('whsec_'): raise SystemExit('STRIPE_WEBHOOK_SECRET must be a test fixture secret in ignored server environment')
    if not base: raise SystemExit('VITE_SUPABASE_URL is required')
    timestamp = str(int(time.time())); signature = hmac.new(secret.encode(), f'{timestamp}.{raw}'.encode(), hashlib.sha256).hexdigest(); request = urllib.request.Request(base.rstrip('/') + '/functions/v1/stripe-webhook', data=raw.encode(), headers={'Content-Type': 'application/json', 'Stripe-Signature': f't={timestamp},v1={signature}', 'apikey': env.get('VITE_SUPABASE_ANON_KEY', '')}, method='POST')
    with urllib.request.urlopen(request, timeout=45) as response: status = response.status
    result.update({'http_status': status, 'submitted_to': 'stripe-webhook', 'live_mode': False}); print_json(result)

if __name__ == '__main__': main()
