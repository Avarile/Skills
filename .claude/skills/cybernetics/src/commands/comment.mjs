import { emit } from '../format.mjs';
import { CybError, EXIT } from '../errors.mjs';

export const COMMENT_COLUMNS = [
  { key: 'created_at', label: 'WHEN' },
  { key: 'text', label: 'COMMENT' },
];

export function escapeHtml(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

function stripHtml(html) {
  return String(html ?? '').replace(/<[^>]*>/g, '').trim();
}

function itemRef(ctx) {
  const ref = ctx.positionals[0];
  if (!ref) throw new CybError(EXIT.GENERAL, 'no work item given', 'example: cyb comment list CYB-42');
  return ref;
}

export async function commentList(ctx) {
  const item = await ctx.resolver.item(itemRef(ctx));
  const { data } = await ctx.client.request(
    'GET',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/comments/`,
  );
  const rows = (data?.results ?? []).map((c) => ({
    id: c.id,
    created_at: c.created_at,
    text: stripHtml(c.comment_html),
  }));
  emit(rows, { mode: ctx.mode, columns: COMMENT_COLUMNS, stdout: ctx.streams.stdout });
}

export async function commentAdd(ctx) {
  const ref = itemRef(ctx);
  const text = ctx.positionals.slice(1).join(' ').trim();
  if (!text) {
    throw new CybError(
      EXIT.GENERAL,
      'no comment text given',
      'example: cyb comment add CYB-42 "looks good"',
    );
  }

  const item = await ctx.resolver.item(ref);
  const { data } = await ctx.client.request(
    'POST',
    `${ctx.client.projectPath(item.projectId)}/issues/${item.id}/comments/`,
    { body: { comment_html: `<p>${escapeHtml(text)}</p>` } },
  );
  emit(data, { mode: ctx.mode, stdout: ctx.streams.stdout });
}
