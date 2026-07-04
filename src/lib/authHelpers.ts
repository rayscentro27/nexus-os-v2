import { supabase } from './supabaseClient';

/**
 * Returns the correct redirect URL for Supabase password recovery emails.
 * Uses goclearonline.cc in production, localhost in dev, with Netlify fallback.
 */
export function getPasswordResetRedirectUrl(): string {
  const origin = window.location.origin;
  if (origin.includes('localhost') || origin.includes('127.0.0.1')) {
    return 'http://localhost:5173/update-password';
  }
  if (origin.includes('goclearonline.cc')) {
    return 'https://goclearonline.cc/update-password';
  }
  if (origin.includes('nexusv20.netlify.app')) {
    return 'https://nexusv20.netlify.app/update-password';
  }
  return `${origin}/update-password`;
}

/**
 * Change the password of the currently authenticated user.
 * Requires an active Supabase session (no old password needed when using session auth).
 */
export async function changeCurrentUserPassword(newPassword: string): Promise<{ error?: string }> {
  if (!supabase) return { error: 'Supabase not configured.' };
  if (newPassword.length < 12) return { error: 'Password must be at least 12 characters.' };
  const { error } = await supabase.auth.updateUser({ password: newPassword });
  if (error) return { error: error.message };
  return {};
}

/**
 * Send a password reset email to the given address.
 * Uses the configured redirect URL for the recovery link.
 * Always shows the same success message regardless of whether the account exists.
 */
export async function sendPasswordResetEmail(email: string): Promise<{ error?: string; sent: boolean }> {
  if (!supabase) return { error: 'Supabase not configured.', sent: false };
  const redirectTo = getPasswordResetRedirectUrl();
  const { error } = await supabase.auth.resetPasswordForEmail(email, { redirectTo });
  if (error) return { error: error.message, sent: false };
  return { sent: true };
}

/**
 * Detect whether the current URL indicates a password recovery session.
 */
export function isRecoverySession(): boolean {
  const params = new URLSearchParams(window.location.search);
  return params.get('password-recovery') === '1' || window.location.hash.includes('type=recovery');
}

/**
 * Update password during a recovery session.
 * Signs out after success and redirects to the login page with a success message.
 */
export async function updateRecoveredPassword(newPassword: string): Promise<{ error?: string }> {
  if (!supabase) return { error: 'Supabase not configured.' };
  if (newPassword.length < 12) return { error: 'Password must be at least 12 characters.' };
  const { error } = await supabase.auth.updateUser({ password: newPassword });
  if (error) return { error: error.message };
  await supabase.auth.signOut();
  window.location.assign('/?password-reset=success');
  return {};
}
