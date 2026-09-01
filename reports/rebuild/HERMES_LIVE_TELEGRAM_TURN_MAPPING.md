# Live Telegram turn mapping

The relevant Phoenix evening sequence is represented by updates 590357273–275
(UTC timestamps are recorded by the worker). Update 590357273 was the initial
Nexus attention request and ended in delivery failure; 590357274 was the review
request and delivered message 1043; 590357275 was the later attention request
and delivered message 1044.

The later morning sequence is updates 590357276–281. All six were processed in
order on session `nova-telegram-primary-1288928049` and delivered messages
1046, 1048, 1050, 1052, 1054, and 1056 respectively. Update 590357276’s final
text was progress-only despite being marked delivered.

The worker logs show no overlapping `Incoming` entries for the morning
sequence. The observed concurrency risk was nevertheless real in code: lock
contention returned false and the poller advanced its offset.
