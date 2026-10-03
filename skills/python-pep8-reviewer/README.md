# python-pep8-reviewer

Agent skill (agentskills.io format) that reviews Python code against PEP 8 and PEP 257 and reports concrete fixes.

- `SKILL.md` — agent skill definition: scope, config overrides, mechanical and judgment passes, severity, report format
- `scripts/pep8_review.py` — mechanical scanner; prints JSON findings with pycodestyle, pyflakes, pep8-naming and pydocstyle codes
- `references/pep8-checklist.md` — checklist for the judgment pass
- `tests/` — pytest suite (`python3 -m pytest tests` from this directory); fixtures are cross-checked against flake8 + pep8-naming + flake8-docstrings when installed
- `CHANGELOG.md` — history of checks and fixes

The scanner has no dependencies beyond the standard library and runs on Python 3.8+. Files under `tests/fixtures/` are deliberately non-compliant test inputs.

```bash
python3 scripts/pep8_review.py path/to/package --line-length 88
```
