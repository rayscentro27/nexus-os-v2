import { describe, it, expect } from 'vitest';
import fs from 'node:fs';

const authSource = fs.readFileSync('src/components/auth.tsx', 'utf8');
const helpersSource = fs.readFileSync('src/lib/authHelpers.ts', 'utf8');
const settingsSource = fs.readFileSync('src/admin/NexusAdminUI.jsx', 'utf8');
const appSource = fs.readFileSync('src/app/App.tsx', 'utf8');
const updatePageSource = fs.readFileSync('src/pages/UpdatePasswordPage.tsx', 'utf8');
const securityPanelSource = fs.readFileSync('src/components/AccountSecurityPanel.tsx', 'utf8');

describe('Password reset and account security', () => {
  describe('Settings Security UI', () => {
    it('AccountSecurityPanel exists', () => {
      expect(securityPanelSource).toContain('Account Security');
      expect(securityPanelSource).toContain('Change password');
      expect(securityPanelSource).toContain('Send password reset email');
    });

    it('Settings page includes AccountSecurityPanel', () => {
      expect(settingsSource).toContain('AccountSecurityPanel');
      expect(settingsSource).toContain('Account Security');
    });

    it('Settings page receives email prop', () => {
      expect(settingsSource).toMatch(/SettingsPage\s+email=\{email\}/);
    });

    it('Security panel displays current email', () => {
      expect(securityPanelSource).toContain('Signed in as');
    });

    it('Security panel has safety note', () => {
      expect(securityPanelSource).toContain('Nexus does not store your password');
    });
  });

  describe('Change password form validation', () => {
    it('validates minimum password length', () => {
      expect(securityPanelSource).toContain('minLength={12}');
    });

    it('validates password confirmation match', () => {
      expect(securityPanelSource).toContain('Passwords do not match');
    });

    it('has new password and confirm fields', () => {
      expect(securityPanelSource).toContain('New password');
      expect(securityPanelSource).toContain('Confirm new password');
    });
  });

  describe('Password is never logged or stored', () => {
    it('auth.tsx does not log passwords', () => {
      expect(authSource).not.toMatch(/console\.\w+\(.*password/i);
    });

    it('authHelpers.ts does not log passwords', () => {
      expect(helpersSource).not.toMatch(/console\.\w+\(.*password/i);
    });

    it('helpers do not use localStorage for passwords', () => {
      expect(helpersSource).not.toContain('localStorage');
      expect(securityPanelSource).not.toContain('localStorage');
    });

    it('helpers do not use writeFile', () => {
      expect(helpersSource).not.toContain('writeFile');
    });
  });

  describe('Reset email flow', () => {
    it('calls resetPasswordForEmail', () => {
      expect(authSource).toContain('resetPasswordForEmail');
    });

    it('uses getPasswordResetRedirectUrl for redirect', () => {
      expect(authSource).toContain('getPasswordResetRedirectUrl');
    });

    it('signInForm has forgot password button', () => {
      expect(authSource).toContain('Forgot password?');
    });

    it('Security panel has send reset email form', () => {
      expect(securityPanelSource).toContain('sendPasswordResetEmail');
    });
  });

  describe('Update password page', () => {
    it('update-password route exists in App.tsx', () => {
      expect(appSource).toContain('/update-password');
      expect(appSource).toContain('UpdatePasswordPage');
    });

    it('UpdatePasswordPage has password and confirm fields', () => {
      expect(updatePageSource).toContain('New password');
      expect(updatePageSource).toContain('Confirm new password');
    });

    it('UpdatePasswordPage validates password length', () => {
      expect(updatePageSource).toContain('minLength={12}');
    });

    it('shows safe error for invalid/expired recovery', () => {
      expect(updatePageSource).toContain('Reset link expired');
      expect(updatePageSource).toContain('Request a new password reset email');
    });

    it('shows back to sign in button when recovery invalid', () => {
      expect(updatePageSource).toContain('Back to sign in');
    });

    it('uses updateRecoveredPassword helper', () => {
      expect(updatePageSource).toContain('updateRecoveredPassword');
    });
  });

  describe('Auth helper does not import service role', () => {
    it('helpers use supabase client not service role', () => {
      expect(helpersSource).toContain("from './supabaseClient'");
      expect(helpersSource).not.toContain('service_role');
      expect(helpersSource).not.toContain('SUPABASE_SERVICE_ROLE');
    });

    it('auth.tsx does not import service role', () => {
      expect(authSource).not.toContain('service_role');
      expect(authSource).not.toContain('SUPABASE_SERVICE_ROLE');
    });
  });

  describe('Existing auto-login/session persistence not broken', () => {
    it('useSession still calls getSession', () => {
      expect(authSource).toContain('getSession()');
    });

    it('useSession still has onAuthStateChange', () => {
      expect(authSource).toContain('onAuthStateChange');
    });

    it('AuthGate still checks recoveryMode', () => {
      expect(authSource).toContain('recoveryMode');
    });

    it('AuthGate still checks user', () => {
      expect(authSource).toContain('if (!user)');
    });
  });

  describe('Redirect URL configuration', () => {
    it('production uses goclearonline.cc', () => {
      expect(helpersSource).toContain('goclearonline.cc');
    });

    it('local dev uses localhost', () => {
      expect(helpersSource).toContain('localhost:5173');
    });

    it('fallback uses nexusv20.netlify.app', () => {
      expect(helpersSource).toContain('nexusv20.netlify.app');
    });

    it('returns /update-password path', () => {
      expect(helpersSource).toContain('/update-password');
    });
  });

  describe('Build and source integrity', () => {
    it('auth.tsx still has SignInForm', () => {
      expect(authSource).toContain('export function SignInForm');
    });

    it('auth.tsx still has AuthGate', () => {
      expect(authSource).toContain('export function AuthGate');
    });

    it('auth.tsx still has useSession', () => {
      expect(authSource).toContain('export function useSession');
    });
  });
});
