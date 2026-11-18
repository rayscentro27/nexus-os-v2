import { describe, expect, it } from 'vitest';
import { mapSystems } from '../admin-app/src/integration/mapLive';

describe('Admin live systems mapping', () => {
  it('does not report an online host as healthy when a service is stopped', () => {
    const [system] = mapSystems({
      systems: [{ id: 'nova', name: 'Nova', role: 'Operator', status: 'ONLINE', services: { hermes: 'STOPPED' } }],
    }, '2026-11-16T00:00:00Z');

    expect(system.status).toBe('DEGRADED');
    expect(system.blocker).toContain('hermes STOPPED');
  });

  it('keeps unknown service status disconnected', () => {
    const [system] = mapSystems({
      systems: [{ id: 'unknown', name: 'Unknown', role: 'Runtime', status: 'UNKNOWN', services: {} }],
    }, null);

    expect(system.status).toBe('NOT_CONNECTED');
  });
});
