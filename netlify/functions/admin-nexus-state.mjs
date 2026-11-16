// NEXUS_FINAL_OVERNIGHT_COMPLETION_R1: authoritative Nexus state for the approved Admin Center.
// Admin-guarded (Supabase session + admin role). Reads the Mac-published read model
// (nexus_admin_read_model, service-role only) and signs private creative previews.
import { requireAdmin } from './_admin-auth.mjs'
import { supabaseRequest } from './_supabase-control-plane.mjs'

const json = (statusCode, body) => ({
  statusCode,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
})
const env = (key) => process.env[key] || ''
const BUCKET = 'creative-assets'
const STALE_AFTER_SECONDS = 20 * 60

async function signPaths(paths) {
  const url = (env('SUPABASE_URL') || env('VITE_SUPABASE_URL')).replace(/\/$/, '')
  const key = env('SUPABASE_SERVICE_ROLE_KEY')
  if (!url || !key || !paths.length) return {}
  const response = await fetch(`${url}/storage/v1/object/sign/${BUCKET}`, {
    method: 'POST',
    headers: { apikey: key, authorization: `Bearer ${key}`, 'content-type': 'application/json' },
    body: JSON.stringify({ expiresIn: 3600, paths }),
  }).catch(() => null)
  const rows = response && response.ok ? await response.json().catch(() => []) : []
  const out = {}
  for (const row of Array.isArray(rows) ? rows : []) {
    if (row?.path && row?.signedURL) out[row.path] = `${url}/storage/v1${row.signedURL}`
  }
  return out
}

export async function handler(event) {
  if (event.httpMethod !== 'GET') return json(405, { error: 'method_not_allowed' })
  const admin = await requireAdmin(event)
  if (!admin.ok) return json(admin.statusCode, { error: admin.error })
  let rows
  try {
    rows = await supabaseRequest('nexus_admin_read_model?select=area,payload,generated_at')
  } catch {
    return json(503, { error: 'nexus_read_model_unavailable', truth: 'NOT_CONNECTED' })
  }
  const areas = Object.fromEntries((Array.isArray(rows) ? rows : []).map((row) => [row.area, row.payload]))
  const creative = Array.isArray(areas.creative) ? areas.creative : []
  const signed = await signPaths(creative.map((asset) => asset.storage_path).filter(Boolean))
  areas.creative = creative.map((asset) => ({
    ...asset,
    thumbnail_url: signed[asset.storage_path] || '',
    preview_data: { ...(asset.preview_data || {}), full_image_url: signed[asset.storage_path] || undefined },
  }))
  const generatedAt = areas.meta?.generated_at || null
  const age = generatedAt ? Math.round((Date.now() - Date.parse(generatedAt)) / 1000) : null
  return json(200, {
    areas,
    generated_at: generatedAt,
    age_seconds: age,
    freshness: age === null ? 'UNKNOWN' : age > STALE_AFTER_SECONDS ? 'STALE' : 'LIVE',
    role: admin.role,
    provenance: 'nexus_admin_read_model published from authoritative Nexus sources (same project reader as Nova)',
  })
}
