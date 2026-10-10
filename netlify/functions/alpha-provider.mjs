const json = (status, body) => ({
  statusCode: status,
  headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
  body: JSON.stringify(body),
});

// External model calls remain disabled until a durable job identity, approval,
// and Resource & Spend Governor reservation can be verified server-side.
export async function handler(event) {
  if (event.httpMethod === 'GET' || event.path?.endsWith('/status')) {
    return json(200, {
      available: false,
      reason: 'governed_durable_job_required',
      externalCallPerformed: false,
    });
  }
  if (event.httpMethod !== 'POST') return json(405, { error: 'method_not_allowed' });
  return json(403, {
    error: 'governed_durable_job_required',
    externalCallPerformed: false,
  });
}
