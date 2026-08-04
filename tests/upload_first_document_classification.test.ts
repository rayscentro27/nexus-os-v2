import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('upload-first document classification', () => {
  const source = fs.readFileSync(path.join(process.cwd(), 'src/components/client/InlineDocumentUpload.jsx'), 'utf8');

  it('does not render category selection before a file exists', () => {
    const chooseFileIndex = source.indexOf('Choose File');
    const confirmationIndex = source.indexOf('needsCategoryConfirmation &&');
    const selectIndex = source.indexOf('aria-label="Confirm document category"');
    expect(chooseFileIndex).toBeGreaterThan(0);
    expect(confirmationIndex).toBeGreaterThan(chooseFileIndex);
    expect(selectIndex).toBeGreaterThan(confirmationIndex);
    expect(source).not.toContain('Select category...');
  });

  it('persists classification status, confidence, and basis in upload metadata', () => {
    expect(source).toContain('classification_status');
    expect(source).toContain('classification_confidence');
    expect(source).toContain('classification_basis');
    expect(source).toContain('CLASSIFIED_HIGH_CONFIDENCE');
    expect(source).toContain('NEEDS_CLIENT_CONFIRMATION');
  });
});
