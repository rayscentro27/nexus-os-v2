# Nova Telegram A/B referent continuity

The A/B hook uses the same Telegram message text and chat-derived conversation
identity for the comparison, while keeping the Hermes shadow session isolated.
It does not alter either runtime's referent behavior. Multiple-referent and
three-resource behavior must be judged from the actual Telegram turns.

`REAL_TELEGRAM_AB_REFERENT_CONTINUITY=NOT_RUN`.
