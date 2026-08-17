import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const SKILL = join(ROOT, 'SKILL.md');

function frontmatter() {
  const text = readFileSync(SKILL, 'utf8');
  const match = /^---\n([\s\S]*?)\n---/.exec(text);
  assert.ok(match, 'SKILL.md must open with YAML frontmatter');
  const fields = {};
  for (const line of match[1].split('\n')) {
    const eq = line.indexOf(':');
    if (eq === -1) continue;
    fields[line.slice(0, eq).trim()] = line.slice(eq + 1).trim().replace(/^"|"$/g, '');
  }
  return fields;
}

test('SKILL.md exists', () => {
  assert.ok(existsSync(SKILL));
});

test('frontmatter has exactly name and description', () => {
  assert.deepEqual(Object.keys(frontmatter()).sort(), ['description', 'name']);
});

test('name is within 64 characters', () => {
  assert.ok(frontmatter().name.length <= 64);
});

test('description is within 1024 characters and states when to use the skill', () => {
  const description = frontmatter().description;
  assert.ok(description.length <= 1024);
  assert.match(description, /use when/i);
});

test('description carries the trigger words from the spec', () => {
  const description = frontmatter().description.toLowerCase();
  for (const word of ['cybernetics', 'plane', 'task', 'projects.avarile.com']) {
    assert.ok(description.includes(word), `description missing trigger word: ${word}`);
  }
});

test('no committed doc contains a live API token', () => {
  for (const file of ['SKILL.md', 'README.md', 'references/api-surface.md', 'references/recipes.md', 'references/troubleshooting.md']) {
    const text = readFileSync(join(ROOT, file), 'utf8');
    assert.ok(!/plane_api_[a-f0-9]{16,}/.test(text), `${file} contains what looks like a real token`);
  }
});

test('SKILL.md body stays lean for progressive disclosure', () => {
  const body = readFileSync(SKILL, 'utf8').replace(/^---[\s\S]*?---/, '');
  assert.ok(body.length < 6000, `SKILL.md body is ${body.length} bytes; keep it under 6000`);
});

test('SKILL.md states the safety rule and the json contract', () => {
  const text = readFileSync(SKILL, 'utf8');
  assert.match(text, /--yes/);
  assert.match(text, /--json/);
  assert.match(text, /confirm/i);
});

test('reference files exist', () => {
  for (const file of ['references/api-surface.md', 'references/recipes.md', 'references/troubleshooting.md']) {
    assert.ok(existsSync(join(ROOT, file)), `missing ${file}`);
  }
});

test('api-surface records the endpoints known to be absent', () => {
  const text = readFileSync(join(ROOT, 'references/api-surface.md'), 'utf8');
  for (const absent of ['estimates', 'attachments', 'sub-issues', 'issue-relation']) {
    assert.match(text, new RegExp(absent));
  }
});
