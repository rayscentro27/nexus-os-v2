import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('active operator runner registry status', () => {
  it('records receipt-only execution as simulated, not completed success', () => {
    const runner = fs.readFileSync(path.join(process.cwd(), 'scripts/operations/nexus_active_operator_runner.py'), 'utf8');
    expect(runner).toContain('process_registry_adapter');
    expect(runner).toContain('return "simulated", details');
    expect(runner).toContain('status="SIMULATED"');
    expect(runner).not.toContain('return "completed", details');
  });
});
