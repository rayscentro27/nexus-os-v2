/**
 * Nexus OS v2 — Client Vault adapter factory.
 *
 * v1 ALWAYS returns the mock adapter. There is no live connection by design: no second Supabase, no
 * real credentials, no real client data. A live adapter is intentionally not implemented yet; the
 * factory refuses to return one.
 */
import type { ClientVaultAdapter } from '../config/clientVaultContract';
import { CLIENT_VAULT_CONNECTION_STATUS, CLIENT_VAULT_CONTRACT_META } from '../config/clientVaultContract';
import { MockClientVaultAdapter } from './mockClientVaultAdapter';

let singleton: MockClientVaultAdapter | null = null;

/** Returns the mock Client Vault adapter. Live mode is not available in v1. */
export function getClientVaultAdapter(): ClientVaultAdapter {
  if (CLIENT_VAULT_CONNECTION_STATUS !== 'not_connected_by_design') {
    // Defensive: even if the status were flipped, v1 has no live implementation.
    throw new Error('Live Client Vault is not connected by design in v1. Use the mock adapter.');
  }
  if (!singleton) singleton = new MockClientVaultAdapter();
  return singleton;
}

export function clientVaultStatus() {
  return {
    connection_status: CLIENT_VAULT_CONNECTION_STATUS, // 'not_connected_by_design'
    adapter_in_use: 'mock' as const,
    second_supabase_connected: CLIENT_VAULT_CONTRACT_META.second_supabase_connected,
    real_credentials_present: CLIENT_VAULT_CONTRACT_META.real_credentials_present,
    real_client_data_present: CLIENT_VAULT_CONTRACT_META.real_client_data_present,
    supported_future_backends: CLIENT_VAULT_CONTRACT_META.supported_future_backends,
  };
}
