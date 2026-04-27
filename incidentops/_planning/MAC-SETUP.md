# Mac Setup — IncidentOps

One-time setup to continue the IncidentOps build from a Mac after cloning. Assumes you have Homebrew, an SSH key registered with GitHub, and Claude Code installed.

## 1. Clone

```bash
mkdir -p ~/projects && cd ~/projects
git clone git@github.com:sapnilbhatnagar/incidentops.git
cd incidentops
```

(If you prefer HTTPS: `git clone https://github.com/sapnilbhatnagar/incidentops.git`.)

## 2. Restore the project memory

Claude Code stores per-project auto-memory under `~/.claude/projects/<encoded-cwd>/memory/`. The encoded directory name is generated automatically the first time you start Claude Code in a working directory. So:

```bash
# Start a Claude Code session once from the cloned repo so the projects/<encoded-cwd>/ folder exists
cd ~/projects/incidentops
claude  # exit immediately with /exit if you want — this just creates the folder
```

Then find the encoded path and copy the vendored memory file into it:

```bash
# Find the auto-created project folder (newest under ~/.claude/projects/)
PROJECT_DIR=$(ls -td ~/.claude/projects/*/ | head -1)
echo "Project memory dir: ${PROJECT_DIR}memory/"

mkdir -p "${PROJECT_DIR}memory"
cp incidentops/_planning/memory/project_tomoro_work_product.md "${PROJECT_DIR}memory/"

# Add a one-line MEMORY.md index entry if MEMORY.md doesn't exist yet
if [ ! -f "${PROJECT_DIR}memory/MEMORY.md" ]; then
  cat > "${PROJECT_DIR}memory/MEMORY.md" <<'EOF'
# Memory Index

- [project_tomoro_work_product.md](project_tomoro_work_product.md) — Active: IncidentOps build for Tomoro.ai application
EOF
else
  # If MEMORY.md exists, append the entry if it's not already there
  grep -q project_tomoro_work_product.md "${PROJECT_DIR}memory/MEMORY.md" || \
    echo "- [project_tomoro_work_product.md](project_tomoro_work_product.md) — Active: IncidentOps build for Tomoro.ai application" >> "${PROJECT_DIR}memory/MEMORY.md"
fi
```

## 3. Verify

```bash
cd ~/projects/incidentops
git log --oneline                                        # should show: chore: scaffold IncidentOps prototype
ls incidentops/data/                                     # runbooks, tickets, incidents, telemetry, reference, gold/
cat incidentops/_planning/build-plan.md | head -5        # plan is in-repo
ls "${PROJECT_DIR}memory/"                               # project_tomoro_work_product.md + MEMORY.md
```

## 4. First Mac session

Start Claude Code in the repo:

```bash
cd ~/projects/incidentops
claude
```

The auto-memory should now load the IncidentOps project context. Open with something like:

> "Resume IncidentOps build. Phase 0 is done. Ready to start Phase 1 (repo scaffold + corpus expansion)."

Claude Code will read the session log and the build plan and pick up where Windows left off.

## Notes

- The `_planning/` directory is for human + agent context, not runtime code. Do not import from it; do not let CI artefacts land in it.
- If you change the project name or move the repo, the encoded `~/.claude/projects/<...>/` folder will change. Re-copy the memory file to the new location.
- Obsidian: the prototype no longer needs to live inside the Obsidian vault. If you still want cross-referencing, symlink `~/Obsidian/.../prototype` to `~/projects/incidentops/`.
