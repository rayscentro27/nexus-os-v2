const PRODUCTION_HOSTS = ['goclearonline.cc', 'www.goclearonline.cc'] as const;

export function getCanonicalOrigin(): string {
  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (PRODUCTION_HOSTS.includes(hostname as typeof PRODUCTION_HOSTS[number])) {
      return 'https://goclearonline.cc';
    }
    return window.location.origin;
  }
  return 'https://goclearonline.cc';
}

export function isProductionHost(hostname: string): boolean {
  return PRODUCTION_HOSTS.includes(hostname as typeof PRODUCTION_HOSTS[number]);
}

export function isRejectedHost(hostname: string): boolean {
  return hostname.includes('netlify.app') || hostname.includes('localhost');
}

export function buildCustomerUrl(path: string): string {
  const origin = getCanonicalOrigin();
  return `${origin}${path.startsWith('/') ? path : `/${path}`}`;
}

export function validateCustomerUrl(url: string): { valid: boolean; reason?: string } {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes('netlify.app')) {
      return { valid: false, reason: 'Rejected host: netlify domain' };
    }
    if (parsed.protocol !== 'https:' && !parsed.hostname.includes('localhost')) {
      return { valid: false, reason: 'Production URLs must use HTTPS' };
    }
    return { valid: true };
  } catch {
    return { valid: false, reason: 'Invalid URL' };
  }
}
