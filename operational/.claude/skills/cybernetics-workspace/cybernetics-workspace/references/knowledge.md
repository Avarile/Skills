# Knowledge (cybernetics-data)

Base `bseJEuE54y5caWO0Xc8`. Two tables: `knowledges` (the entries) and `knowledge_type` (categories for entries). Both are hierarchical (parent/child).

## Contents
- Tables and fields
- Workflows: capture, find, organise, archive
- Rules of thumb

## Tables and fields

### `knowledges` - `tblVTWb1kxXSFPBq4Fq`
| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldROFj15OlD8COVxX0` | Short, searchable, specific |
| context | `fld5tr2rH8oJXLrjUo9` | Markdown body |
| knowledge_type | `fldAEK8ULw9urxE0qiF` | Link -> `knowledge_type` (many entries : one type) |
| knowledge_parent | `fldzUUVy3q1vSWURhZD` | Link -> `knowledges` (self, parent entry) |
| related_knowledge | `fldz7U2RsCfm0j1RZOs` | Link -> `knowledges` (many-many, symmetric "see also") |
| is_active | `fldZKMuaBBPd6tIzSG3` | Checkbox, default true |
| deleted_at | `fldNS9SNNWG07NnBZhE` | Date, set when archived |

Read-only / reverse: `knowledges` `fldKzPJEFtElf4liepG` (children, filled automatically by `knowledge_parent`), `created_at`, `updated_at`, `id`.

### `knowledge_type` - `tblWcq6Kof1AFHvbC5e`
| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldvL1LqKmEAfNKVBCO` | Type name |
| context | `fldsnpIqBqoYZJxZwI5` | Markdown: what belongs in this type |
| credentials | `fld1s2dEom17aZIu4nx` | **Sensitive.** Single-line text. Do not read/echo/write unless the user asks for it specifically |
| parent_type | `fld924GlXY0tL5um2wk` | Link -> `knowledge_type` (self, one-way) |
| is_active | `fldte086UL30roxKKAl` | Checkbox |
| deleted_at | `fldMcIaV4FSsuV9OG9J` | Date |

Read-only / reverse: `knowledges` `fldtBWHVokGwcAywjtc` (entries of this type), `child_types` `fldehPY6CjjdpeK3H6j`, `created_at`, `updated_at`, `id`.

## Workflows

**Capture a new entry**
1. Search first: `query_records` on `knowledges` with `search` = the topic. If a close entry exists, offer to update it (append a dated section) rather than create a near-duplicate.
2. Pick the type: `query_records` on `knowledge_type` (projection: title, context). Choose the best fit. If none fits, propose a new type and ask before creating it, because types are a shared taxonomy.
3. Create the entry with `title`, Markdown `context`, and `knowledge_type` set to the type record's ID (see "Link values" in SKILL.md for the shape).
4. If it belongs under a larger topic, set `knowledge_parent`. If it connects to other entries, set `related_knowledge`.
5. Show the user the title, type and a short excerpt of what was saved.

**Find / recall**
- `query_records` with `search`; add `projection` = title, knowledge_type, updated_at to scan quickly, then `get_record` for the one or two that matter.
- Answer from the entry text and name the entry title you used. If nothing is found, say so rather than answering from memory as if it were stored knowledge.

**Update**
- Preserve existing `context`. Add new information as a new section with the date, or edit the specific part requested. Don't overwrite the whole field unless asked.

**Organise**
- Moving an entry = update `knowledge_type` and/or `knowledge_parent`. Restructuring a type tree = update `parent_type`. Reorganising many entries at once counts as a bulk write: list the planned moves and get confirmation.

**Archive**
- Set `is_active` = false and `deleted_at` = today. Exclude inactive entries in normal searches.

## Rules of thumb

- Write entries so future-you can use them cold: what it is, when it applies, the steps or facts, and any caveats. Prefer Markdown headings and bullets.
- Never store passwords, API tokens or keys inside `context`. If the user wants access info recorded, describe where it lives and how to obtain it (e.g. "in the password manager under X"), and only use `credentials` if they explicitly instruct it.
- Entries that describe how to use the user's own tools (like this workspace) are good candidates for a `knowledge_type` such as "How-to"; check what types exist before inventing one.
