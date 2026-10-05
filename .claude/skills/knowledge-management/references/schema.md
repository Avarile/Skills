# Schema reference (captured 2026-10-05)

Base `bseJEuE54y5caWO0Xc8` ("data-centre"). IDs are stable unless the user restructures a table. On "field not found": `GET /api/table/<id>/field` (or MCP `get_table_schema`), continue with fresh IDs, and tell the user this file is stale.

## REST API

Base URL `https://cybernetics.avarile.com`, token `CYBERNETICS_DATA_API_TOKEN` (env or `.env`; never print it). `GET /api/table/<tableId>/record` with `fieldKeyType=id`, `take` (<=1000), `skip`, repeated `projection[]=<fieldId>`, JSON `filter`, `orderBy`. `scripts/kb.py` wraps all of it.

### Verified behaviours (2026-10-05, live)

- **The `search` parameter in the generated API docs (`temp/api-doc-*`) is wrong.** `search=john` returns HTTP 400 ("expected tuple"). It is a tuple: `search[]=<value>&search[]=<fieldId or empty for all>&search[]=true`. `kb.py` uses `filter` + `contains` instead (same speed, combinable).
- `contains` is **case-insensitive** on title and context. Nested filters work: `and(or(title contains x, context contains x), type isAnyOf [...], is_active is true)`.
- Link filters: `isAnyOf` / `isNoneOf` on `knowledge_type` (rows with no type are kept by `isNoneOf`); `hasAnyOf` on many-to-many links.
- Default Python-urllib User-Agent gets HTTP 403; `teable.py` sends a curl UA.
- One filtered query over all 133 rows including bodies: 0.1-0.5 s.
- **`related_knowledge` is effectively one-way.** Its `symmetricFieldId` (`fldTvK8TAoC33yBFbqa`) points to a field that no longer exists. A link written on A does not appear on B. `kb.py` writes both sides.
- **`knowledge_type.parent_type` is one-way** (`isOneWay: true`) and **`child_types` is a separate, independent link** (its symmetric field `fldhCf1NQf4Tl4VDFMN` is also gone; empty on every row). Build the type tree from `parent_type` only; never write `child_types`.
- `knowledge_parent` / `knowledges` (children) **are** a proper pair: write `knowledge_parent`, children fill in.
- Link titles in a read can lag a write by a moment (`title` missing right after a PATCH). Ids are correct immediately.
- Create defaults: send `is_active: true` explicitly. Unchecked checkbox reads as missing/`null`.
- Dates read back as UTC timestamps; convert to Australia/Melbourne (`teable.local_date`).
- Hard delete (`DELETE /record?recordIds=`) goes to the table trash. Normal archive is soft: `is_active` false + `deleted_at`.

## knowledges `tblVTWb1kxXSFPBq4Fq`

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldROFj15OlD8COVxX0` | `<Subject> - <Aspect>` |
| context | `fld5tr2rH8oJXLrjUo9` | Markdown body; median ~200 chars, max ~38k |
| knowledge_type | `fldAEK8ULw9urxE0qiF` | many-to-one -> knowledge_type (reverse `knowledge_type.knowledges` fills) |
| knowledge_parent | `fldzUUVy3q1vSWURhZD` | many-to-one -> knowledges: part of a series / sub-document |
| knowledges | `fldKzPJEFtElf4liepG` | children, read-only reverse of knowledge_parent |
| related_knowledge | `fldz7U2RsCfm0j1RZOs` | many-to-many "see also"; one-way in practice, write both sides |
| is_active / deleted_at | `fldZKMuaBBPd6tIzSG3` / `fldNS9SNNWG07NnBZhE` | soft delete |
| id / created_at / updated_at | `fldNxPGGDuchpHCvz0U` / `fldRs8i67CkuzpDyubP` / `fldCpv0ts2jxxgQPg7n` | read-only |

## knowledge_type `tblWcq6Kof1AFHvbC5e`

| Field | ID | Notes |
|---|---|---|
| title (primary) | `fldvL1LqKmEAfNKVBCO` | `<domain> - <topic>` |
| context | `fldsnpIqBqoYZJxZwI5` | what belongs in this type (empty on all 42 today) |
| credentials | `fld1s2dEom17aZIu4nx` | single line text; returned by `kb.py type` (CR-1) |
| parent_type | `fld924GlXY0tL5um2wk` | many-to-one self link, one-way; the only tree link |
| child_types | `fldehPY6CjjdpeK3H6j` | independent, unused; do not write |
| knowledges | `fldtBWHVokGwcAywjtc` | entries of this type, read-only reverse |
| is_active / deleted_at | `fldte086UL30roxKKAl` / `fldMcIaV4FSsuV9OG9J` | |
| id / created_at / updated_at | `fldD6MxhSrpatAbHd0k` / `fldAPzS5RXnhHUrVlmu` / `fld1TMYMRUBblTyTIuU` | read-only |

## Links from work (project-management)

`refer_knowledge` is a one-way many-to-many link on the work record; knowledge has no reverse field, so "what uses this entry" is one `hasAnyOf` query per table.

| Table | Table ID | refer_knowledge | title |
|---|---|---|---|
| goals | `tblbGSzWdR7KEtPVClg` | `fldRMySX5jvdIUWIkGB` | `fld8ipvRLGq7YTgPQkI` |
| projects | `tbliD8gcOTRk9RZ9SmR` | `fldCw3cnpw8EWs09C1v` | `fldiDksJhyT8mDAhCBP` |
| tasks | `tblOMgDiajqa1moRRjE` | `fldJzsKyzBaDFt7bHIu` | `fldGqUoXO7oyq6ufX2Y` |

Write the whole array: read current ids, add, PATCH, read back (`kb.py` `add_link`). Never send only the new id (it would replace the others).

## Link write shapes

Reads return `{ "id": "recXXX", "title": "..." }`. Many-to-one write `{ "id": "recXXX" }`; many-to-many write `[{ "id": "recXXX" }, ...]`; clear with `null`.

## State notes (2026-10-05)

133 entries (all active; 4 untyped; 1 with a parent; 0 related), 42 types (flat except `missav_meta` -> `missav_meta_Ayumi_Ryo`; no descriptions), 0 `refer_knowledge` links from goals/projects/tasks. Clean-up groups A-F are planned in project "Knowledge Management Skill" Step 13.
