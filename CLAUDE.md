# CLAUDE.md

Short entrypoint for Claude or any other agent landing at the actual Git root.

## Important first fact

The actual Git root is:

- `C:\Users\WINDOWS\Documents`

But the intended project lives here:

- `C:\Users\WINDOWS\Documents\gym`

Do not assume the whole `Documents` tree is part of the product.

## Read order

1. `C:\Users\WINDOWS\Documents\gym\AGENTS.md`
2. `C:\Users\WINDOWS\Documents\gym\ARCHITECTURE.md`
3. `C:\Users\WINDOWS\Documents\gym\SPEC.md`
4. `C:\Users\WINDOWS\Documents\gym\HANDOFF.md`

## Fast facts

- Main reference builder:
  - `C:\Users\WINDOWS\Documents\gym_try.py`
- Main backend:
  - `C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py`
- Main UI:
  - `C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input_ui.py`
- Versioned content should be `.py`, `.md`, `.gitignore`, and the four canonical reference CSVs
- Videos, non-canonical CSVs, `.task`, images, and `ui_runs/` are local runtime artifacts and should stay out of Git

## Recommended behavior

- Treat `gym\AGENTS.md` as the primary operational guide.
- Treat CSV headers and string labels as cross-file contracts.
- Expect local runtime assets to be missing from Git.
