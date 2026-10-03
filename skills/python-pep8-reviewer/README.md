# python-pep8-reviewer

Agent skill (agentskills.io format) that reviews Python code against PEP 8 and PEP 257 and reports concrete fixes.

- `SKILL.md` — agent skill definition: scope, config overrides, mechanical and judgment passes, severity, report format
- `scripts/pep8_review.py` — mechanical scanner; prints JSON findings with pycodestyle (layout, blank lines, whitespace, statements), pyflakes, pep8-naming and pydocstyle codes
- `references/pep8-checklist.md` — checklist for the judgment pass
- `tests/` — pytest suite (`python3 -m pytest tests` from this directory); fixtures are cross-checked against flake8 + pep8-naming + flake8-docstrings when installed
- `CHANGELOG.md` — history of checks and fixes

The scanner has no dependencies beyond the standard library and runs on Python 3.8+. Files under `tests/fixtures/` are deliberately non-compliant test inputs.

## Usage

Run from this directory.

```bash
# Mechanical scan with defaults (line length 79, doc length 72)
python3 scripts/pep8_review.py path/to/package

# With custom limits (e.g., Black's line length of 88)
python3 scripts/pep8_review.py path/to/package --line-length 88 --doc-length 72

# Run the test suite
python3 -m pytest tests
```

Output is JSON: `{"files": N, "line_length": 79, "doc_length": 72, "findings": [{"path", "line", "code", "message"}, ...]}`. Exit code 0 means no findings, 1 means findings, 2 means no Python files were found.
