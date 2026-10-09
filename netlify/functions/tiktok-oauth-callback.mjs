import { json } from './_tiktok.mjs'

export async function handler(_event) {
  return json(503, { error: 'provider_governance_unavailable', status: 'disabled_fail_closed' })
}
