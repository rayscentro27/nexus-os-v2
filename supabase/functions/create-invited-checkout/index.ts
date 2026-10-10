// Fail-closed safe-mode endpoint. Provider execution remains disabled until a governed job contract is implemented.
const ERROR_CODE = "PROVIDER_PAYMENT_CHECKOUT_DISABLED_PENDING_GOVERNANCE";
Deno.serve((request: Request) => {
  const headers = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
    "Content-Type": "application/json",
  };
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
  return new Response(JSON.stringify({ error: ERROR_CODE }), { status: 503, headers });
});
