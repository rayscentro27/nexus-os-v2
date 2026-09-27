import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import { mapRouteToV2, ROUTE_LABELS } from '../src/client-v2/utils/navigate';

describe('client profile and settings routes', () => {
  it('maps canonical client aliases to the approved V2 surfaces', () => {
    expect(mapRouteToV2('/client/profile')).toBe('/client-v2/profile');
    expect(mapRouteToV2('/client/settings')).toBe('/client-v2/settings');
    expect(ROUTE_LABELS['/client-v2/profile']).toBe('My Profile');
    expect(ROUTE_LABELS['/client-v2/settings']).toBe('Settings');
  });

  it('uses the existing client profile contract and keeps sensitive fields out', () => {
    const profile = fs.readFileSync('src/client-v2/approved/components/views/ProfileView.tsx', 'utf8');
    const settings = fs.readFileSync('src/client-v2/approved/components/views/SettingsView.tsx', 'utf8');
    expect(profile).toContain('loadClientProfileIntake');
    expect(profile).toContain('saveClientProfileIntake');
    expect(profile).toContain('checkProfileIntakeComplete');
    expect(profile).toContain('never enter a full EIN');
    expect(profile).not.toMatch(/\bssn\b|social security number/i);
    expect(settings).toContain('resetPasswordForEmail');
    expect(settings).toContain('Communication preferences');
  });
});
