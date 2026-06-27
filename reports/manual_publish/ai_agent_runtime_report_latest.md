# AI Agent Runtime Report

- generated_at: 2026-06-27T01:36:18.501905+00:00

## Enforcement matrix (role × method)
### hermes_ceo_advisor
- allow: exportSanitizedSignals
- deny: listClientProfiles, getCreditReport, getCreditScoreSnapshots, getBusinessProfile, listBusinessSetupItems, listProofUploads, listLetterPackets, listMailingRecords, listWorkflowTasks, listReminderTasks, getFundingReadiness, listAffiliateAttribution, listConsentEvents

### researcher_ai
- allow: none
- deny: listClientProfiles, getCreditReport, getCreditScoreSnapshots, getBusinessProfile, listBusinessSetupItems, listProofUploads, listLetterPackets, listMailingRecords, listWorkflowTasks, listReminderTasks, getFundingReadiness, listAffiliateAttribution, listConsentEvents, exportSanitizedSignals

### credit_specialist_ai
- allow: listClientProfiles, getCreditReport, getCreditScoreSnapshots, getBusinessProfile, listBusinessSetupItems, listProofUploads, listLetterPackets, listMailingRecords, listWorkflowTasks, listReminderTasks, getFundingReadiness, listAffiliateAttribution, listConsentEvents, exportSanitizedSignals
- deny: none

### funding_specialist_ai
- allow: listClientProfiles, getCreditReport, getCreditScoreSnapshots, getBusinessProfile, listBusinessSetupItems, listProofUploads, listLetterPackets, listMailingRecords, listWorkflowTasks, listReminderTasks, getFundingReadiness, listAffiliateAttribution, listConsentEvents, exportSanitizedSignals
- deny: none

### business_setup_specialist_ai
- allow: listClientProfiles, getCreditReport, getCreditScoreSnapshots, getBusinessProfile, listBusinessSetupItems, listProofUploads, listLetterPackets, listMailingRecords, listWorkflowTasks, listReminderTasks, getFundingReadiness, listAffiliateAttribution, listConsentEvents, exportSanitizedSignals
- deny: none

### client_chat_ai
- allow: listClientProfiles, getCreditReport, getCreditScoreSnapshots, getBusinessProfile, listBusinessSetupItems, listProofUploads, listLetterPackets, listMailingRecords, listWorkflowTasks, listReminderTasks, getFundingReadiness, listAffiliateAttribution, listConsentEvents
- deny: exportSanitizedSignals

## Sample audit log
- hermes_ceo_advisor · raw_credit_report · allowed=False · hermes_ceo_advisor blocked from tool client_vault_adapter.
- hermes_ceo_advisor · sanitized_signal · allowed=True
- researcher_ai · raw_credit_report · allowed=False · researcher_ai blocked from tool client_vault_adapter.
- researcher_ai · sanitized_signal · allowed=False · researcher_ai blocked from tool sanitized_client_signals.
- credit_specialist_ai · raw_credit_report · allowed=True
- credit_specialist_ai · sanitized_signal · allowed=True
- funding_specialist_ai · raw_credit_report · allowed=True
- funding_specialist_ai · sanitized_signal · allowed=True
- business_setup_specialist_ai · raw_credit_report · allowed=True
- business_setup_specialist_ai · sanitized_signal · allowed=True
- client_chat_ai · raw_credit_report · allowed=True
- client_chat_ai · sanitized_signal · allowed=False · client_chat_ai blocked from tool sanitized_client_signals.
