-- Ray Review routing hardening for synthetic tester feedback.
-- The partial expression index makes repeated admin clicks idempotent even when
-- two requests race. The payload remains summary-only and approval-gated.
create unique index if not exists task_requests_tester_feedback_ray_review_uidx
  on public.task_requests ((payload->>'feedback_record_id'))
  where task_type = 'ray_review_item'
    and requested_by = 'tester_feedback'
    and payload ? 'feedback_record_id';

comment on index public.task_requests_tester_feedback_ray_review_uidx is
  'One approval-gated Ray Review draft per synthetic tester_feedback record';
