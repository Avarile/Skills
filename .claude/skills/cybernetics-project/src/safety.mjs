import { CybError, EXIT } from './errors.mjs';

// The command surface in this iteration has no bulk-mutation command, so
// BULK_THRESHOLD has no call site yet. It is exported and tested so the
// spec's bulk rule has one authoritative value when such a command lands.
export const BULK_THRESHOLD = 10;

export function requireConfirmation(ctx, { action, targets }) {
  if (ctx.values?.yes) return;
  const list = targets.join(', ');
  throw new CybError(
    EXIT.REFUSED,
    `refusing to ${action} without confirmation: ${list}`,
    'confirm with the user, then pass --yes',
  );
}
