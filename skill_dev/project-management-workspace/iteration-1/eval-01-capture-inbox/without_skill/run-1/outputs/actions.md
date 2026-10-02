## Calls made
- ToolSearch select: list_tables, get_table_schema, query_records
- list_tables baseId=bseJEuE54y5caWO0Xc8
- get_table_schema tblOMgDiajqa1moRRjE (tasks)
- query_records projects tbliD8gcOTRk9RZ9SmR search="staging" take=10
- query_records tasks tblOMgDiajqa1moRRjE search="SSL" take=10 (projection title/progress/priority/project)

## Proposed writes
create_records on tblOMgDiajqa1moRRjE with one record, fields:
- fldGqUoXO7oyq6ufX2Y (title): "Renew the SSL certificate for staging"
- fldMTuydiWUFAgtqAPX (priority): "urgent"
- fldG7fZN9XhOa0lMy33 (progress): "backlog"
- fld6X3nrMTQlYiV5XSa (belong_project): link to recGMngbWlVQCq9jzaC (Inbox)
Ask user to confirm (and whether to use k3s Migration recNEeZTYI9Z2KQyvXm instead).
