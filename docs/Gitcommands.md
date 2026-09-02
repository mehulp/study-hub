# Git Commands — Reference

A working reference of common git commands, grouped by when you'd reach for them. Not exhaustive — just the ones that come up in normal solo-project workflow.

## Setup (one-time)
- `git config --global user.name "..."` / `user.email "..."` — your commit identity, stored in `~/.gitconfig`.
- `git init` — turns a folder into a git repo (creates the hidden `.git/` directory that stores all history).

## The daily loop
- `git status` — what's changed, what's staged, what's untracked. The "where am I" command — run it constantly, before anything risky.
- `git diff` — shows *unstaged* changes, line by line (`-` removed, `+` added). Run this before `git add` to review what you're about to stage.
- `git diff --staged` — same, but for changes already staged (what would actually go into the next commit).
- `git add <file>` — stages a file (marks it "ready for the next commit"). `git add -A` stages everything, including deletions — use carefully, prefer naming files.
- `git commit -m "message"` — takes everything staged and creates a permanent snapshot (a "commit") in history.
- `git log` — history of commits. `git log --oneline` compresses each to one line.
- `git show <commit>` — full detail (diff + metadata) of one specific commit. `git show HEAD` shows the most recent one.

## Branching
- `git branch` — lists branches; `git branch -m <name>` renames the current one (used once, to rename `master` → `main`).
- `git switch -c <name>` (or older `git checkout -b <name>`) — creates and switches to a new branch. Useful for isolating a new endpoint/feature from `main` until it's ready.
- `git switch <name>` — switch to an existing branch.
- `git merge <name>` — merges another branch's commits into your current branch.

## Remote (relevant once connected to GitHub)
- `git remote add origin <url>` — links this local repo to a remote (e.g. a GitHub repo).
- `git push -u origin main` — uploads local commits to the remote; `-u` remembers this pairing so future pushes are just `git push`.
- `git pull` — fetches + merges remote changes into your current branch.
- `git clone <url>` — copies an existing remote repo down to a new local folder (what you'd run on a different machine).

## Undoing things (worth understanding before you need them)
- `git restore <file>` — discards *unstaged* changes to a file, reverting it to the last commit. Destructive — the change is gone.
- `git restore --staged <file>` — unstages a file (moves it from staged back to unstaged) without touching its content.
- `git reset --soft HEAD~1` — undoes the last commit but keeps the changes staged. Useful for "I committed too early."
- `git revert <commit>` — creates a *new* commit that undoes an old one, instead of rewriting history. Safe for anything already pushed/shared, since it doesn't erase the original commit.
- `git stash` — temporarily shelves uncommitted changes (handy when you need a clean working tree to switch branches mid-work); `git stash pop` brings them back.

The four used in nearly every session: `status`, `diff`, `add`, `commit`. Everything else gets reached for situationally.
