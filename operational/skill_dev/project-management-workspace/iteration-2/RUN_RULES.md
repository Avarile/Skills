# Rules for this benchmark run

You are handling one request from the user, Avarile. It is Tuesday 2026-11-03 in Melbourne. Your working directory is `/Users/avarilewang/Documents/agentSkills/operational`. The user's data is in the cybernetics-data database: base `bseJEuE54y5caWO0Xc8`, tools `mcp__cyb-data__*` (load them with ToolSearch).

## The database must not change

This is a live database and this is a read-only test run.

- Do not call any MCP tool that creates, updates or deletes (`create_records`, `update_record`, `delete_records` and so on).
- Do not call the REST API to write.
- If you use a skill script, never pass `--yes`. Dry runs are fine.
- Do not send anything to anyone, and do not edit any file outside your outputs folder. Put any working files, such as a plan JSON, in your outputs folder.

When the request calls for a write, go as far as showing the user what would be written and asking for confirmation, then stop. List the exact writes you would make under `## Actions`.

## The user is not available, so simulate the conversation

Write the whole conversation to `outputs/response.md`, exactly as the user would see it:

- Start each message you would send with `ASSISTANT:`.
- If a message ends in a question, write the user's reply on the next line as `USER (simulated):`, taking your recommended option, or the obvious answer if you made no recommendation. Then carry on.
- Finish when the task is done, or when you reach the point of asking to confirm a write. Do not simulate that confirmation.

Then add a final section `## Actions` listing the commands and tool calls you actually ran, and the writes you would make on confirmation.

Do not read the `project-management-workspace` folder other than this file and your own outputs folder. Your final reply to whoever started you is one line: `done`.
