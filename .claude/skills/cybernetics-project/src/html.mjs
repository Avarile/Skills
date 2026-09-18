// Shared by every command that builds an `*_html` field for the API: comment
// bodies (comment.mjs) and work item descriptions (item.mjs). Escapes the
// three characters that matter when the text lands in element content —
// never an attribute — so pasted text containing `<`, `>` or `&` (a code
// snippet, "a < b", "Foo & Bar") survives instead of being parsed as markup,
// and arbitrary HTML can't be smuggled into a stored field. See Important 4.
export function escapeHtml(text) {
  return String(text)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}
