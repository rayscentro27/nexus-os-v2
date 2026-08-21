import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

describe('active operator runner authority contract', () => {
  it('uses a closed-world bounded runner with explicit safety states', () => {
    const runner = fs.readFileSync(path.join(process.cwd(), 'scripts/operations/nexus_active_operator_runner.py'), 'utf8');
    expect(runner).toContain('process_registry_adapter');
    expect(runner).toContain('create_pending_work_order');
    expect(runner).toContain('AUTO_EXECUTE_INTERNAL_SAFE');
    expect(runner).toContain('APPROVAL_REQUIRED');
    expect(runner).toContain('NOT_AUTHORIZED');
    expect(runner).toContain('stripe_autonomous_execution');
    expect(runner).toContain('SKIPPED_OVERLAP');
  });
});
