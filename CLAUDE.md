# CLAUDE.md

This file provides guidance for AI assistants (Claude and others) working in this repository.

## Project Overview

**Name:** bull

**State:** Early-stage / bootstrapping. The repository currently contains only a `README.md`. No source code, build system, or configuration files have been added yet.

**Repository:** `raikan/bull` (hosted at `http://local_proxy@127.0.0.1:24904/git/raikan/bull`)

---

## Repository Structure

```
bull/
├── README.md      # Project title only
└── CLAUDE.md      # This file
```

As development begins, this section should be updated to reflect the actual directory layout (e.g., `src/`, `tests/`, `docs/`, etc.).

---

## Git Workflow

### Branch Conventions

- **Default branch:** `master`
- **Claude working branches:** Follow the pattern `claude/<description>-<session-id>`
  - Example: `claude/claude-md-mlxs3blpmp3e8cwv-BwDY6`

### Commit Conventions

Use clear, descriptive commit messages. Prefer the imperative mood:

```
Add user authentication module
Fix null pointer in queue processor
Update README with setup instructions
```

### Push

Always push with tracking:

```bash
git push -u origin <branch-name>
```

---

## Development Setup

No build system or runtime has been established yet. When one is chosen, document the following here:

- **Language / runtime** (e.g., Node.js, Python, Go)
- **Dependency installation** (e.g., `npm install`, `pip install -r requirements.txt`)
- **Build command** (e.g., `npm run build`, `make`)
- **Run command** (e.g., `npm start`, `./bin/bull`)

---

## Testing

No test framework is configured yet. When one is added, document:

- **Test runner** (e.g., Jest, Pytest, Go test)
- **How to run tests** (e.g., `npm test`)
- **How to run a single test file**
- **Coverage reporting** (if applicable)

---

## Linting and Formatting

No linters or formatters are configured yet. When added, document:

- **Linter** (e.g., ESLint, flake8, golangci-lint)
- **Formatter** (e.g., Prettier, black, gofmt)
- **How to run checks** (e.g., `npm run lint`)
- **Whether checks run in CI**

---

## CI/CD

No CI/CD pipeline is configured. When set up, document:

- **CI provider** (e.g., GitHub Actions, CircleCI)
- **Workflow triggers** (e.g., on push to `master`, on pull request)
- **Required checks before merge**

---

## AI Assistant Guidelines

When working in this repository:

1. **Update this file** (`CLAUDE.md`) whenever you add or change something significant — new build scripts, test commands, project structure, conventions.
2. **Keep `README.md` in sync** with the current state of the project (purpose, setup, usage).
3. **Do not assume a language or framework** has been chosen until source files or config files confirm it.
4. **Prefer editing existing files** over creating new ones unless explicitly required.
5. **Follow the git branch convention** — all Claude working branches must start with `claude/` and include the session ID suffix.
6. **Avoid over-engineering** — add only what is asked for or clearly necessary.
7. **Commit and push changes** at the end of each working session on the designated branch.
