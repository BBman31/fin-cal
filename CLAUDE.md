# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->


## Build & Test

```bash
uv sync
uv run streamlit run app.py
uv run pytest
uv run ruff check .
```

## Architecture Overview

Streamlit app (`app.py` + `views/`), logic in `fincal/` (pure pandas, testable).
Spending log is read-only from `data/spending_log.xlsx`; settings/mappings/open-close live in
`data/settings.yaml`. `data/` is gitignored (real finances); `examples/` holds fake data.

## Conventions & Patterns

- Keep calculations in `fincal/metrics.py` as pure functions; pages only render.
- Never commit anything under `data/`.

## Git Workflow

One branch per beads issue, one PR per branch, merged on GitHub. This repo opts in:
agents may commit, push feature branches and open PRs without asking. They must never
push to `main`, merge locally, or merge PRs.

1. **Pick and claim:** `bd ready`, then `bd update <id> --claim`.
2. **Branch from up-to-date `main`:** `git checkout main && git pull`, then
   `git checkout -b <type>/<bead-id>-<short-slug>`.
   Types are `feat/`, `fix/` and `chore/`, for example `feat/fc-jeo-per-month-income`.
   - If the work depends on a PR that isn't merged yet, branch from that PR's branch and
     use it as the new PR's base. GitHub retargets the PR to `main` once the base merges,
     because head branches are auto-deleted.
3. **Commit** in small, focused commits. End the message with `Refs: <bead-id>`.
   Before every push, run `uv run ruff format . && uv run ruff check . && uv run pytest`.
4. **Open the PR** when the issue is done: push the branch and run
   `gh pr create --base main` (or the stacked base). Give the PR a title in imperative
   mood. The body says what changed and why, how it was verified, and `Beads: <bead-id>`.
   Anything that couldn't be verified is stated plainly.
5. **Merge** only on GitHub, only by the user, with a merge or rebase. No squash, because
   squashing breaks stacked PRs.
6. **After the merge:** `bd close <id>`, then `git checkout main && git pull`.
   Follow-up work gets a new bead and a new branch; don't reopen a merged branch.

Never commit anything under `data/`. Keep unrelated changes (tooling, generated files)
out of feature PRs.
