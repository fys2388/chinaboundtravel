/**
 * Buffer dedup / tracking helpers (pure functions, no I/O).
 * Shared by worker.js and unit tests. ESM (.mjs) so Node can import it directly.
 */

/**
 * Build a stable dedup identity for a publish task.
 * Returns null when contentId is missing (caller must fall back to the legacy dedup key).
 */
export function buildDedupKey({ contentId, account, platform, variant }) {
  const cid = (contentId || '').trim();
  if (!cid) return null;
  const acc = (account || 'default').trim();
  const plat = (platform || 'unknown').trim();
  const varKey = (variant || 'default').trim() || 'default';
  return `dedup:${cid}:${acc}:${plat}:${varKey}`;
}

/**
 * Build an internal tracking record for a publish task.
 * Used as a KV metadata blob; never exposed in user-visible social copy.
 */
export function buildTrackRecord({ contentId, platform, account, scheduledAt, sourceWorkflow, postUrl }) {
  return {
    content_id: contentId || '',
    platform: platform || '',
    account: account || '',
    scheduled_at: scheduledAt || '',
    source_workflow: sourceWorkflow || '',
    post_url: postUrl || '',
  };
}

/**
 * Whether a task should be skipped because the same
 * content_id + account + platform + variant was already posted.
 */
export function isDuplicate({ contentId, account, platform, variant, existing }) {
  if (!contentId) return false;
  const key = buildDedupKey({ contentId, account, platform, variant });
  if (!key) return false;
  return Boolean(existing);
}
