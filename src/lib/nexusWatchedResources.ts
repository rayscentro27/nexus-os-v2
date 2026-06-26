import type { NexusWatchedResource } from '../config/nexusWatchedResources';

export function watchedResourceReviewLabel(resource: Pick<NexusWatchedResource, 'enabled' | 'approved_by_ray' | 'watch_status'>): string {
  if (!resource.approved_by_ray) return 'Needs Ray approval';
  if (!resource.enabled) return 'Saved, disabled';
  if (resource.watch_status === 'new_items_found') return 'New items found';
  return 'Ready for manual watch check';
}

export function watchedResourceNextAction(resource: Pick<NexusWatchedResource, 'resource_type' | 'approved_by_ray' | 'enabled'>): string {
  if (!resource.approved_by_ray) return 'Approve this resource before watch/backfill.';
  if (!resource.enabled) return 'Enable only after Ray approves watch mode.';
  if (resource.resource_type.startsWith('youtube')) return 'Run manual watch dry-run; transcript review remains bounded.';
  return 'Run manual metadata/RSS dry-run; no broad scraping.';
}

export function countEnabledWatchedResources(resources: NexusWatchedResource[]): number {
  return resources.filter((resource) => resource.enabled && resource.approved_by_ray).length;
}
