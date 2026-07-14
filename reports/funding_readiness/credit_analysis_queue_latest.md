# Credit Analysis Queue

The deployed-safe interim trigger is option B: authenticated admins insert into `credit_analysis_jobs`; admin-only RLS and a partial unique index prevent more than one queued/processing job per document. The browser never receives the service-role key.

`process_credit_analysis_queue.py --once` claims only queued credit-analysis jobs, runs the verified parser and system review, records parser/review IDs, and exits. `--max-jobs` is capped at 10. It is not a daemon and has no letter or DocuPost integration.

Live fake-job proof: job `7ad18f32-8a9f-48f8-a807-62efcc30b97e` progressed queued → processing → complete.
