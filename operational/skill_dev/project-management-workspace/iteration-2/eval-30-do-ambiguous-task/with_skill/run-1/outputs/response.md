ASSISTANT: Three tasks match "create video", all in backlog under Cyberneutica marketing. None has a due date, priority above normal, or a block today:

1. How to use AI Agents, from the basics to Pro
2. AI Native human being transformation, from digitizing yourself to advanced AI adoption
3. AI adoption, where almost everyone gets it wrong

I recommend 1. It's first in your project brief, and it covers the basics the other two build on.

Which one should I do?

USER (simulated): 1.

ASSISTANT: I've drafted the script for "How to use AI Agents, from the basics to Pro". I can't produce the video itself, so you'd still record the demos and the voiceover. Nothing is saved to the database yet.

The task says "Details to be completed by the owner" and has no acceptance criteria, so there was nothing to check the draft against. I made these choices, so change any that are wrong:

- **Audience:** solo operators who already use a chatbot, taken from your Product Marketing Context.
- **Length:** about 8 minutes with the demos: 5 of speaking and about 3 of screen recording.
- **Voice:** calm and declarative, as in your brand voice notes.
- **Selling:** one line about Cybernetics at Level 5 and no pitch, because your brief keeps these videos separate from Knowledge for Fee. The call to action is left open.

Before you record:

- **Product claim:** the Level 5 line says every agent works from one shared record. Your marketing context still marks that as "to confirm".
- **Your input:** Level 4 needs a real story from you, and I didn't invent one. The demos are yours to record, so keep private data off screen.
- **Name:** the project says "Cyberneutica", but your knowledge base and goal say "Cybernetics". The script uses "Cybernetics".

---

# How to use AI agents, from the basics to pro

Draft script. About 8 minutes with the demos: 5 minutes of speaking, plus about 3 minutes of screen recording. Screen directions are in [brackets]. Each [DEMO] is a screen recording you make yourself, and each [YOUR EXAMPLE] needs a real story from you.

## Cold open (0:00)

Most people use AI like this. [Screen: a chat window.] Ask a question. Read the answer. Copy it somewhere else. Do the work yourself.

An agent works differently. You give it a goal, and it does the work.

In the next eight minutes we go through five levels, from your first agent task to agents that run part of your day. Each level adds one skill. Stop at the level you need.

## What an agent is (0:40)

A chatbot produces text. An agent takes actions.

It runs a loop. It looks at the goal. It picks a step. It uses a tool: reads a file, runs a search, updates a record. It looks at the result. Then it picks the next step, until the goal is met or it gets stuck.

[Screen: the loop drawn as goal, step, tool, result, back to step.]

That loop is the whole idea. Everything else in this video is about making it reliable.

## Level 1: Give it one small job (1:30)

Start with work that is small, boring and easy to check. Sort these files. Summarise this folder. Find every invoice from last month.

Say three things: what you want, where the material is, and what done looks like.

"Rename the files in this folder by date. Show me the list before you change anything."

[DEMO: one small task, from prompt to result.]

The mistake at this level is starting too big. You can't judge an agent on a job you couldn't check yourself.

## Level 2: Give it context (2:30)

An agent starts with what you give it. If it knows nothing about you, you get generic work, and you spend the session re-explaining yourself.

So write it down once. Who you are, how you work, what good looks like, what never to do. Put that in an instructions file the agent reads at the start of every session.

[DEMO: the same request, with and without the instructions file.]

The instructions don't have to be long. They have to be true. Each time you correct the agent, ask whether that correction belongs in the file.

## Level 3: Give it tools, and limits (3:45)

An agent can only act through the tools you connect: your files, your calendar, your database.

Connect one at a time. Start read-only. Let it see before you let it change.

Then decide what it can do alone and what needs your approval. A simple rule: if a mistake is easy to undo, let it run. If a mistake leaves your building, such as an email, a payment, a deletion or a deploy, it asks first.

[DEMO: the agent stopping to ask before it sends something.]

## Level 4: Make it prove the work (4:45)

Agents sound confident, including when they are wrong. "Done" from an agent is a claim. It isn't evidence.

So define the check before the work starts. The tests pass. The totals match the source. Every figure has a link.

Then ask for the evidence along with the output. Better still, give the review to a second agent that didn't do the work.

[YOUR EXAMPLE: a time an agent said done and the check caught it.]

This is the level that separates people who trust agents from people who gave up on them.

## Level 5: Run it as a system (5:45)

You now have an agent that knows your context, has tools, and proves its work. The last level is to stop starting from zero.

Three moves.

Turn repeated work into written procedures, so the agent follows the same steps each time.

Put recurring work on a schedule, so the weekly report is ready before you ask.

Keep the memory outside the chat, in one record you own: your knowledge, projects and decisions. Then any agent can read it and write back to it, and switching tools costs you nothing.

[DEMO: one agent picks up a task, reads what an earlier session recorded, finishes, and writes back.]

That last move is why I'm building Cybernetics. What you know and do is persisted, day after day, and every agent works from that record.

## The ladder (7:00)

[Screen: the five levels as a list.]

One small job. Written context. Tools with limits. Proof of work. A system that remembers.

Don't climb it all this week. Pick the level you're on, and do the next one once.

## Close (7:30)

Your first step today: choose one boring task you did this week. Give it to an agent. Say what done looks like, and check the result.

[Call to action: your choice. This video is separate from Knowledge for Fee, so this draft does not pitch it.]

---

If you confirm, I'll make these writes:

1. **Start the work:** create an adhoc block and today's plan row, since today has no plan. Move the task from `backlog` to `in-progress` with `started_at` set, and assign it to you, since it's unassigned.
2. **Save the script:** append it to the task's generated output.
3. **Add a log line:** "2026-11-03 Draft script stored in agentic_generation. Not recorded yet; task stays in-progress."

The task stays `in-progress`, because a script isn't a finished video. I'd leave the block open until you've reviewed the draft, then ask how many minutes you spent on it.

Shall I make these three writes?

## Actions

**Commands run** (all read-only or dry-run; `--yes` was never passed, and no MCP write tools were called). Paths are relative to `.claude/skills/project-management/scripts/`, except the `kb.py` calls, which are in `.claude/skills/knowledge-management/scripts/`.

- `python3 taskctx.py "create video"`: exit 4, 3 matches
- `python3 taskctx.py "video"`: exit 4, the same 3 matches
- `python3 query.py tblOMgDiajqa1moRRjE --project fldGqUoXO7oyq6ufX2Y --search video --take 50`: failed with HTTP 400 (`search` validation error), so it returned nothing
- `python3 query.py tblOMgDiajqa1moRRjE --project fldGqUoXO7oyq6ufX2Y --filter 'fldGqUoXO7oyq6ufX2Y contains video' --take 50`: 3 rows, so the 3-match list was not cut off
- `python3 day.py now`: no plan today, nothing scheduled, 2026-11-02 not closed
- `python3 taskctx.py reczYTjZyx7CA2ZSQKK --no-knowledge --json --gen-chars 300`, and the same for `recdp55tcK2GDrfMgfX` and `recxFtZh95Hq6UjTktV`
- `python3 taskctx.py reczYTjZyx7CA2ZSQKK --json`: no linked knowledge, and the 3 suggestions were unrelated
- `python3 kb.py find AI agent`, then `Cyberneutica`, `digitization`, `marketing`, `video` and `agentic`
- `python3 kb.py get recVCfPl8EF14j4QcLA` (Product Marketing Context)
- `python3 kb.py get recmErPjEI0TTPy05zx --max-chars 4000` (Pitch Strategy Overview)
- `python3 write.py gen-append --help`, `python3 write.py ctx-append --help`, `python3 day.py start --help`
- `python3 day.py start --task reczYTjZyx7CA2ZSQKK`: dry run
- `python3 write.py gen-append tblOMgDiajqa1moRRjE reczYTjZyx7CA2ZSQKK --prompt "..." --context "..." --model "claude-opus-5-5" --text-file outputs/video-script.md`: dry run, +4793 chars, 0 existing kept. I changed the script's timing note after this run, so the final count differs slightly.
- `python3 write.py ctx-append tblOMgDiajqa1moRRjE reczYTjZyx7CA2ZSQKK --field fldaOhjcXqdiF3IRVB1 --section "## Log" --text "..."`: dry run

**Files written:** `outputs/video-script.md` and `outputs/response.md` only.

**Writes I would make on confirmation:**

```
python3 day.py start --task reczYTjZyx7CA2ZSQKK --yes

python3 write.py gen-append tblOMgDiajqa1moRRjE reczYTjZyx7CA2ZSQKK \
  --prompt "Draft video script: How to use AI Agents, from the basics to Pro" \
  --context "task + project brief + 2 knowledge (Product Marketing Context, Pitch Strategy Overview)" \
  --model "claude-opus-5-5" --text-file outputs/video-script.md --yes

python3 write.py ctx-append tblOMgDiajqa1moRRjE reczYTjZyx7CA2ZSQKK \
  --field fldaOhjcXqdiF3IRVB1 --section "## Log" \
  --text "2026-11-03 Draft script stored in agentic_generation. Not recorded yet; task stays in-progress." --yes
```

**Later, once you give me the minutes:** `python3 day.py finish BLOCK --status partial --minutes N --yes`. `BLOCK` is the id that `day.py start` creates.
