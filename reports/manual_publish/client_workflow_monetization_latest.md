# Client Workflow Monetization

- timestamp: 2026-06-27T01:53:10.319966+00:00
- status: ok
- dry_run: True
- external_action: false · money_spent: false · level_3_blocked: true

## Task -> revenue mapping
- choose_credit_report_source: credit_monitoring affiliate · partner=SmartCredit · DIY=AnnualCreditReport.com (free) · rev=70 · funding=low
- connect_smartcredit_or_upload_report: credit_monitoring affiliate · partner=SmartCredit · DIY=Manual upload · rev=70 · funding=low
- approve_dispute_letters: mailing affiliate · partner=DocuPost · DIY=USPS Certified Mail · rev=55 · funding=low
- confirm_business_entity: business_formation affiliate · partner=Formation partner · DIY=State SoS (DIY) · rev=70 · funding=medium
- add_ein: business_formation affiliate · partner=Formation partner · DIY=IRS.gov (free) · rev=40 · funding=low
- add_business_bank_account: online_business_bank affiliate · partner=Bluevine (primary) · DIY=Client's own bank · rev=75 · funding=high
- add_duns_profile: business_credit_profile affiliate · partner=Business credit tool · DIY=Free DUNS (D&B) · rev=60 · funding=medium
- add_vendor_accounts: vendor_credit affiliate · partner=Vendor credit partner · DIY=Net-30 vendors (DIY) · rev=60 · funding=medium
- upload_bank_statements: funding readiness · partner=None · DIY=From client bank · rev=50 · funding=high
- complete_funding_readiness_review: funding commission pipeline · partner=None · DIY=None · rev=80 · funding=high
- review_recommended_funding_path: funding commission pipeline · partner=None · DIY=None · rev=85 · funding=high

## Examples
- credit report missing -> SmartCredit or free report option
- no score -> SmartCredit recommendation
- LLC missing -> formation affiliate or state DIY
- EIN missing -> guided option or IRS DIY
- business bank missing -> online bank partner or client's own bank
- letters ready -> DocuPost or USPS certified mail
- client stuck -> reminder/upsell
- client nearly funding-ready -> Ray Review/funding path
