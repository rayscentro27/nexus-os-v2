# Google resource transition matrix

| Transition | Result |
| --- | --- |
| Casual → Google | Google tools remain available and are selected only when the question benefits from Google. |
| Google Calendar → casual | General recurring-revenue reasoning used no tool. |
| Google Gmail → casual | General partnership reasoning used no tool. |
| Google → Nexus | Existing Nexus resource selection remains available without a mode switch. |
| Nexus → Google | Calendar/Gmail capabilities remain selectable without a mode switch. |
| Casual → Nexus | Existing Nexus current-state contract remains primary for internal operational questions. |
| Nexus + Calendar | Both selected and synthesized in one turn. |
| Nexus + Gmail | Both selected and synthesized in one turn. |

The implementation uses resource-family metadata (`GOOGLE`) and bounded linked
referent data rather than question-specific routing. Google availability does
not create an obligation to call Google on ordinary turns.
