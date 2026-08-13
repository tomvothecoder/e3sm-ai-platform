# AI Coding Guidance

- Use Ruff as the formatter and lint checker, and `ty` as the type checker.
- Run Ruff after edits; it is authoritative.
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
- Preserve a final newline in files.
