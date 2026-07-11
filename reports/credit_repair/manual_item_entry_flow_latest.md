# Manual Item Entry Flow

Manual item entry is now available from the Credit Specialist Workbench after selecting an uploaded report.

## Fields

- Bureau
- Item type
- Furnisher/account name
- Masked account last 4 only
- Reason
- Notes
- Evidence needed

## Safety

- No SSN field.
- No full DOB field.
- No full account number field.
- No bureau username/password fields.
- Items are labeled specialist-entered and remain in specialist review.

## Save Behavior

The form opens or creates a credit repair case first, then inserts a structured `credit_report_items` row using `createManualReportItem`. It does not create letters automatically.
