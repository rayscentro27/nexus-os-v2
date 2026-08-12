/**
 * Compliance & Enrollment — UI/data contract foundation.
 *
 * This module defines the enrollment record shape for the business-model-aligned
 * operating model (GoClear brand → Nexus OS portal → CRJ / DisputeForMe fulfillment).
 *
 * It is a CONTRACT FOUNDATION ONLY. No final legal language is generated here.
 * Every attorney-required document is represented by a placeholder that must be
 * replaced with the approved version. Nothing here certifies compliance.
 */

export type SignatureStatus = 'unsigned' | 'pending_esign' | 'signed' | 'declined';

export type ConsentStatus = 'not_provided' | 'provided' | 'withdrawn';

export type CancellationStatus = 'active' | 'cancel_requested' | 'cancelled' | 'expired';

export type PaymentAuthorizationStatus = 'not_authorized' | 'authorized' | 'revoked';

export interface ComplianceItemView {
  key: string;
  label: string;
  status: SignatureStatus | ConsentStatus | CancellationStatus | PaymentAuthorizationStatus | 'pending';
  placeholder?: boolean;
  note: string;
}

export interface ComplianceEnrollmentView {
  serviceAgreementVersion: string | null;
  disclosures: ComplianceItemView[];
  signatureStatus: SignatureStatus;
  cancellationDeadline: string | null;
  cancellationStatus: CancellationStatus;
  paymentAuthorization: PaymentAuthorizationStatus;
  communicationConsent: ConsentStatus;
  marketingSource: string | null;
  vendorAuthorization: ConsentStatus;
  privacyConsent: ConsentStatus;
  retentionDate: string | null;
}

/**
 * Builds the enrollment record. `record` is the persisted source of truth when
 * available; otherwise a neutral "pending" foundation is returned so the UI never
 * fabricates a signature or consent that does not exist.
 */
export function buildComplianceEnrollmentView(record?: Partial<ComplianceEnrollmentView> | null): ComplianceEnrollmentView {
  const base: ComplianceEnrollmentView = {
    serviceAgreementVersion: record?.serviceAgreementVersion ?? null,
    disclosures: [
      { key: 'service_agreement', label: 'Service Agreement', status: record?.signatureStatus === 'signed' ? 'signed' : 'unsigned', placeholder: true, note: 'Attorney-approved placeholder — replace before enrollment.' },
      { key: 'dispute_services_authorization', label: 'Outsourced Dispute Services Authorization', status: record?.vendorAuthorization === 'provided' ? 'signed' : 'unsigned', placeholder: true, note: 'Authorizes CRJ / DisputeForMe as the outsourced fulfillment provider.' },
      { key: 'credit_education_disclosure', label: 'Credit Education & No-Guarantee Disclosure', status: record?.signatureStatus === 'signed' ? 'signed' : 'unsigned', placeholder: true, note: 'Nexus never guarantees deletions, score increases, or funding.' },
      { key: 'privacy_consent', label: 'Privacy & Data Handling Consent', status: record?.privacyConsent ?? 'not_provided', note: 'Client PII is tenant-isolated and never shared with Alpha research.' },
      { key: 'communication_consent', label: 'Communication Consent', status: record?.communicationConsent ?? 'not_provided', note: 'Email/SMS/portal consent for journey updates.' },
      { key: 'payment_authorization', label: 'Payment Authorization', status: record?.paymentAuthorization ?? 'not_authorized', note: 'Pay-per-delete charges require verified outcomes before billing.' },
      { key: 'cancellation_policy', label: 'Cancellation Policy', status: record?.cancellationStatus ?? 'active', note: 'Cancellation deadline is recorded from the signed agreement date.' },
    ],
    signatureStatus: record?.signatureStatus ?? 'unsigned',
    cancellationDeadline: record?.cancellationDeadline ?? null,
    cancellationStatus: record?.cancellationStatus ?? 'active',
    paymentAuthorization: record?.paymentAuthorization ?? 'not_authorized',
    communicationConsent: record?.communicationConsent ?? 'not_provided',
    marketingSource: record?.marketingSource ?? null,
    vendorAuthorization: record?.vendorAuthorization ?? 'not_provided',
    privacyConsent: record?.privacyConsent ?? 'not_provided',
    retentionDate: record?.retentionDate ?? null,
  };
  return base;
}

export const COMPLIANCE_FOUNDATION_NOTE =
  'Compliance foundation only. Attorney-approved documents are required before enrollment is complete. Nothing here is certified legal compliance.';
