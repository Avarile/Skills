## Calls made
- ToolSearch select: cyb-data list_tables, get_table_schema, query_records
- list_tables (base bseJEuE54y5caWO0Xc8)
- get_table_schema tasks (tblOMgDiajqa1moRRjE)
- query_records projects search "k3s"
- query_records contacts search "Anastasia"
- query_records tasks search "k3s" (projection title/assigned_to/progress; unhelpful, matched everything)
- get_record tasks reclNpFIo4Ii4zzQ0pD, recMVQZSGtN3BTDycAY, recuEDtppP1Z17ZgNHw

## Proposed writes
Three update_record calls on table tblOMgDiajqa1moRRjE, setting field fld3ZGyfGzogzwHt5Md (assigned_to) to the contact recoD5RMWtQ1osYGBKs (Anastasia Wang):
- recordId reclNpFIo4Ii4zzQ0pD (Step 09 [CHECK])
- recordId recMVQZSGtN3BTDycAY (Step 10 [CHECK])
- recordId recuEDtppP1Z17ZgNHw (Step 11 [ACT])
Ask the user to confirm before running, and whether Step 09 should go to Anastasia.
