# AI Coding Guidance

- Agents may always run pytest, Ruff, ty, and other repository QA tools without
  requesting permission.
- Run the full test, formatting, lint, and QA suite once at final integration
  verification, not after each incremental change; use focused checks earlier
  only when needed to diagnose a concrete failure.
- Use Ruff as the formatter and lint checker, and `ty` as the type checker.
- Run Ruff at final integration verification; it is authoritative.
- Workspace commands:
  - `uv run --all-packages ruff format backend evaluation`
  - `uv run --all-packages ruff check backend evaluation`
  - `uv run --all-packages ty check`
  - `uv run --all-packages pre-commit run --all-files`
- New or modified public modules, classes, and functions should use NumPy-style docstrings.
- Existing code may lack full docstrings; do not make broad, unrelated cleanup changes.
- Use logical blank-line groupings for imports, setup, core logic, and result construction.
- Use two blank lines between top-level definitions. Avoid decorative whitespace.
- Put a blank line before a final `return` only when it separates completed computation from returning a result.
- Keep a module's intended public functions together near the top, after its public types,
  and order them by the user-facing workflow.
- Prefix implementation-only functions with `_`; do not expose internal helpers as public
  module API without a consumer-driven reason.
- Apply Ruff formatting and linting to changed Python files, and run `ty` to type-check
  the affected code before final integration verification.
- Preserve a final newline in files.
