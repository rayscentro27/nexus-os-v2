import { supabase } from '../lib/supabaseClient';
import type { SocialAccount, SocialPost } from '../types/db';

export async function listSocialAccounts(): Promise<SocialAccount[]> {
  if (!supabase) return [];
  const { data, error } = await supabase.from('social_accounts').select('*').order('platform');
  if (error) {
    console.warn('[social] listSocialAccounts:', error.message);
    return [];
  }
  return (data ?? []) as SocialAccount[];
}

export async function listSocialPosts(limit = 25, status?: string): Promise<SocialPost[]> {
  if (!supabase) return [];
  let q = supabase.from('social_posts').select('*').order('created_at', { ascending: false }).limit(limit);
  if (status) q = q.eq('status', status);
  const { data, error } = await q;
  if (error) {
    console.warn('[social] listSocialPosts:', error.message);
    return [];
  }
  return (data ?? []) as SocialPost[];
}
