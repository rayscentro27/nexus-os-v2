import { describe, expect, it } from 'vitest';
import fs from 'node:fs';

describe('Nexus Operator Console foundation', () => {
  it('owns a distinct protected route and does not replace legacy admin', () => {
    const app = fs.readFileSync('src/app/App.tsx', 'utf8');
    expect(app).toContain("const isOperator = path === '/operator'");
    expect(app).toContain('<OperatorConsole email={user.email} />');
    expect(app).toContain('NexusAdminUI');
  });

  it('uses honest foundation statuses and the canonical Creative library', () => {
    const source = fs.readFileSync('src/operator/OperatorConsole.tsx', 'utf8');
    expect(source).toContain("fetch('/creative-library/index.json')");
    expect(source).toContain('No fabricated alerts');
    expect(source).toContain('FOUNDATION');
    expect(source).toContain('CreativeReviewStudio');
    expect(source).toContain('Publication, spend, and outreach remain governed elsewhere.');
  });

  it('defines responsive operator design tokens and review hierarchy', () => {
    const css = fs.readFileSync('src/operator/operator.css', 'utf8');
    expect(css).toContain('@media(max-width:680px)');
    expect(css).toContain('.operator-attention-grid');
    expect(css).toContain('.operator-status-warn');
    expect(css).toContain('.operator-sidebar');
  });
});
