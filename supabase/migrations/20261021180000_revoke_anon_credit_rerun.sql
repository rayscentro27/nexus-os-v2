-- Credit-analysis reruns are an explicit active-admin recovery operation.
-- Anonymous callers do not need RPC visibility; authentication still does
-- not bypass the function's nexus_is_active_admin() guard.
revoke all on function public.request_credit_analysis_rerun(text,text) from public,anon;
grant execute on function public.request_credit_analysis_rerun(text,text) to authenticated,service_role;
