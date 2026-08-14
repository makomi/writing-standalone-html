# 0005 - Install the skill manually into the skills directory

- Status: accepted
- Date: 2026-08-14
- Supersedes: none

## Context

Claude Code discovers personal skills in `~/.claude/skills/`. The agent's
sandbox cannot write there — a direct `mkdir` attempt returns
`Read-only file system`. The restriction is deliberate: a skill directory
is executable surface, so an agent that could write into it could grant
itself new behavior.

## Decision

Build and maintain the skill as its own git repository outside the skills
directory, and install it with one manual command:

```
mv /home/data/home-dir/dev/0_TEMP/writing-standalone-html ~/.claude/skills/
```

or keep the repo where development happens and link it:

```
ln -s <repo path> ~/.claude/skills/writing-standalone-html
```

The symlink route is untested — confirm the skill is discovered before
relying on it.

## Consequences

- Installation is a human step. The skill cannot install or update itself
  in place, by design.
- The repo stays independently versioned and committable, matching the
  per-skill convention already used for `creating-idea-files` and
  `conducting-ims-audit`.
- The build path is recorded in the spec, so a future session does not
  have to rediscover the sandbox limit.
- `update.sh` and ingest mode both operate on the repo, wherever it sits.
  Nothing in the skill hardcodes the installed location.

## Alternatives rejected

**Write directly to `~/.claude/skills/`.** Not available; the sandbox
denies it.

**Relax the sandbox to permit it.** Possible, but it removes a guardrail
for a one-command convenience. Not worth the trade.
