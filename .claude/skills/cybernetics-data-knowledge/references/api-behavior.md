# Verified API behaviour — knowledges & knowledge_type

Every row below was probed live against `https://cybernetics.avarile.com`
on 2026-09-19 (Teable fork). Records created during probing were deleted;
both tables were verified back at their original counts (`knowledges` 131,
`knowledge_type` 42).

Tables: `knowledges` = `tblVTWb1kxXSFPBq4Fq`, `knowledge_type` = `tblWcq6Kof1AFHvbC5e`.

## Where the published docs are wrong

| Doc claim | Reality |
|---|---|
| `search=john` does a full-text search | **Rejected**: `400 expected tuple, received string`. Must be repeated/array (`search[]=john`). |
| `search` narrows results | **It does not filter at all.** `search[]=zzzznotarealstring` returned all 131 records. It only reorders matches first. Use `filter` + `contains`. |
| `filter`/`orderBy` `fieldId` **MUST** be a field ID | Field **names** work too — `{"fieldId":"title",...}` sorts and filters correctly. IDs also work. A name that is not a field gives 400. |

`search[]=docker&search[]=title` (2nd element = field) was accepted but did
not scope the result either: all-fields, title-only and context-only each
returned 131. With a 3rd element `true` (exact) the count changed to 23 —
still not a dependable filter. **Treat `search` as unusable on this instance.**

## What to use instead: an OR of `contains`

`{"conjunction": "or"}` works, so one request can search several fields:

```json
{"conjunction":"or","filterSet":[
  {"fieldId":"title","operator":"contains","value":"docker"},
  {"fieldId":"context","operator":"contains","value":"docker"},
  {"fieldId":"knowledge_type","operator":"contains","value":"docker"}]}
```

Verified: matches the single-field `and` baseline for a rare term, and a
nonsense query returns **0** records — the thing `search` fails to do.

Two traps:

- **An unknown field name in a `filterSet` does not raise.** It contributes
  nothing and the query silently narrows. (An unknown field in `orderBy` *does*
  400.) Take field names from `client.SEARCHABLE`, never by hand.
- **Operators are field-type specific.** `contains` on a single-select or
  checkbox returns `400 Invalid record condition operator for field`; those
  need `is`. This is not about spaces in field names — `Signed Amount` and
  `% Used` both filter fine.

Fields verified to accept `contains`:

| Table | Fields |
|---|---|
| `knowledges` | `title`, `context`, `knowledge_type` |
| `knowledge_type` | `title`, `context`, `credentials`¹ |

¹ accepts `contains` but is excluded from the default search set: it holds real
secrets and no normalizer returns it, so a hit could not be explained.

Link fields match on the **linked record's primary value**, which is why
`--field knowledge_type` finds entries by their type name. This was confirmed
on the base's `finance_*` tables too, where `Payee contains "Coles"` returned
121 transactions by matching the linked payee's name rather than an id. Those
tables are out of scope for this skill, but the rule is a property of the
instance and applies to any link field you filter on.

## Read operations

| Operation | Result |
|---|---|
| `GET /record` both tables | works |
| `take` / `skip` pagination | works; distinct pages |
| `take=1000` | max. `take=1001` → `400 Can't take more than 1000 records` |
| `projection=title` | works |
| `filter` `contains` on `title` | works — 13 real hits for "docker" |
| `filter` `is` on `is_active` (checkbox, `true`) | works |
| `filter` `isEmpty` on a link field | works |
| `filter` `is` on a link field, value = `rec...` id | works (used for "by type") |
| `filter` `isNotEmpty` on text | works |
| `orderBy` by field ID or name, `asc`/`desc` | works |
| `orderBy` unknown field | 400 |
| `GET /record/{id}` | works |
| `GET /record/{missing}` | `404 Can not get record` |

## Write operations

| Operation | Result |
|---|---|
| `POST /record`, one record | works |
| `POST /record`, several records in one call | works — prefer this over N calls |
| `POST` with `fields: {}` | **creates a blank record** (no title required). `is_active` defaults to `true`. |
| `POST` `title` as a number | `400 expected string` — no type coercion |
| `PATCH /record/{id}` | partial; omitted fields keep their values |
| `PATCH /record` (batch, `records:[{id,fields}]`) | **works, undocumented.** Returns an array. |
| `PATCH` a read-only field (`id`, `created_at`) | `400 No field values to set` (read-only keys are stripped, then nothing is left) |
| `PATCH` an unknown field | `404 Field "x" does not exist` — the error helpfully lists every valid key |
| `DELETE /record/{id}` | works; returns the deleted record |
| `DELETE /record?recordIds[]=a&recordIds[]=b` | **works, undocumented.** Batch delete. |
| `DELETE` an already-deleted id | `500 Record repository did not provide the required stored snapshot` — never blind-retry a partial batch |
| `DELETE` a malformed id | `400 Invalid recordId` |

**DELETE responses key `fields` by field ID, not name**, whatever
`fieldKeyType` you sent. `client.decode_deleted()` maps them back.

## Link fields

Write shape is `{"id": "rec..."}` for manyOne and `[{"id": "rec..."}]` for
arrays. Confirmed:

- `{"title": "..."}` **without** an id → `400 expected string ... at id`.
  Titles in responses are decoration; ids are the contract.
- A non-existent `rec...` id → `400 Invalid RecordId`.
- `null` clears a manyOne link. `[]` clears an array link.

### `knowledge_parent` ↔ `knowledges` are ONE relationship

They are the two sides of a single self-referencing link, not independent
fields. Verified with three fresh records:

| Write | Effect |
|---|---|
| `C1.knowledge_parent = P` | `P.knowledges` becomes `[C1]` |
| `P.knowledges = [C2]` | `C2.knowledge_parent = P`, **and C1 is orphaned** (`C1.knowledge_parent → null`) |
| `P.knowledges = [C1,C2]` | both children reparented to P |
| `P.knowledges = []` | all children detached |

**Writing `knowledges` replaces the whole child set.** Reparenting one entry
is safer done from the child (`knowledge_parent`), which is what
`kb parent` does.

### `related_knowledge` is one-directional

A manyMany self-link, but **not** symmetric: after `A.related = [B]`,
`B.related` stayed `null` (checked after a settle delay). A mutual link needs
both records written — `kb relate --mutual`.

### Reverse sides lag ~1s

Immediately after `C.knowledge_parent = P`, reading `P.knowledges` returned
`null`; the same read 1.5s later returned `[C]`. **Read-after-write is not
immediately consistent** for the far side of a link. Don't assert on it in a
tight loop.

## Field notes

- `is_active` defaults to **`true`** on create. An unchecked box is stored and
  returned as `null`, not `false` — coerce with `bool()`.
- `deleted_at` is a plain writable datetime, not a soft-delete mechanism: the
  API does not filter on it. As of the probe, 0 of 131 records set it.
- `id` is a read-only autonumber, **not** reused after deletes (it reached 151
  while only 131 records existed). `POST` responses do not include it — re-read
  the record if you need the number.
- `credentials` on `knowledge_type` is an ordinary single-line text field.
  Treat its contents as sensitive; don't echo it into logs or output.

## Infrastructure quirks

- Cloudflare fronts the instance and blocks the default `Python-urllib/x.y`
  User-Agent with `403` / error `1010`. Send a browser-like UA.
- Homebrew Python on macOS may raise `CERTIFICATE_VERIFY_FAILED`; fall back to
  `/etc/ssl/cert.pem`. Both are handled in `src/client.py`.
