import type { StructuredIntelligenceResult } from './intelligenceTypes';

export type StructuredValidator<T> = (candidate: unknown) => { success: true; data: T } | { success: false; errors: StructuredIntelligenceResult<T>['errors'] };

export function validateStructuredIntelligenceResult<T>(
  candidate: unknown,
  validator: StructuredValidator<T>,
  options: { attempts?: number; sourceModel?: string; evidenceIds?: string[] } = {},
): StructuredIntelligenceResult<T> {
  const result = validator(candidate);
  if (result.success) {
    return {
      success: true,
      data: result.data,
      errors: [],
      attempts: Math.max(1, options.attempts ?? 1),
      sourceModel: options.sourceModel,
      evidenceIds: options.evidenceIds ?? [],
    };
  }
  return {
    success: false,
    errors: result.errors.map((error) => ({
      path: error.path,
      code: error.code || 'SCHEMA_VALIDATION_FAILED',
      message: error.message || 'Structured output failed validation.',
    })),
    attempts: Math.min(Math.max(1, options.attempts ?? 1), 3),
    sourceModel: options.sourceModel,
    evidenceIds: options.evidenceIds ?? [],
  };
}
