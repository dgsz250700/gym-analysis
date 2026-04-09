# AGENTS

Fast entrypoint for any coding agent working on this project.

If you only read one file, read this one first.

Then read these files in order:

1. `ARCHITECTURE.md`
2. `SPEC.md`
3. `HANDOFF.md`

## TL;DR

- Actual Git root: `C:\Users\WINDOWS\Documents`
- Logical project root: `C:\Users\WINDOWS\Documents\gym`
- Main reference builder: `C:\Users\WINDOWS\Documents\gym_try.py`
- Main analysis backend: `C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py`
- Main UI wrapper: `C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input_ui.py`
- Supported exercise today: Bulgarian Split Squat only
- Versioned content should be `.py`, `.md`, `.gitignore`, and the four canonical reference CSVs
- Runtime also depends on local assets that are intentionally not versioned:
  - source videos
  - non-canonical generated CSVs
  - `.task` model files
  - image references

## Read this before changing anything

- Do not assume the Git root and project root are the same.
- Do not assume a fresh clone is runnable by itself.
- Do not infer architecture from files inside `bulgarian/`; many of them are local artifacts.
- Do not rename Spanish string labels unless you update both pipelines.

## Canonical paths

- Reference builder:
  - `../gym_try.py`
- Backend:
  - `bulgarian/gym_input.py`
- UI:
  - `bulgarian/gym_input_ui.py`
- Default model path used by backend:
  - `gym/pose_landmarker_full.task`
- Default reference CSVs expected by backend:
  - `gym/bulgarian/bulgarian_segment_averages.csv`
  - `gym/bulgarian/bulgarian_angles.csv`
  - `gym/bulgarian/bulgarian_angle_changes.csv`

Versioned CSV exceptions:

- `gym/bulgarian/bulgarian_angle_changes.csv`
- `gym/bulgarian/bulgarian_angles.csv`
- `gym/bulgarian/bulgarian_interpolated_segments.csv`
- `gym/bulgarian/bulgarian_segment_averages.csv`

## Canonical vocabulary

- `baja_a_sube`
  - canonical event label in code and CSVs
  - means the motion changed from descending to ascending
- `sube_a_baja`
  - canonical event label in code and CSVs
  - means the motion changed from ascending to descending
- `segment_type`
  - exact format: `start_change_direction|end_change_direction`
- `INTEREST_FIELDS`
  - `knee_angle_deg`
  - `torso_inclination_abs_deg`
  - `neck_inclination_abs_deg`

## Active code surface

### `../gym_try.py`

Purpose:

- build the reference dataset from local reference videos

Main outputs:

- `bulgarian_angles.csv`
- `bulgarian_angle_changes.csv`
- `bulgarian_interpolated_segments.csv`
- `bulgarian_segment_averages.csv`

Important note:

- this file uses mostly Spanish function names

### `bulgarian/gym_input.py`

Purpose:

- process one input video
- compare it against the reference
- render the overlay video

Functions to know first:

- `run_analysis(...)`
- `process_video(...)`
- `build_segment_definitions(...)`
- `build_interpolated_segments(...)`
- `build_segment_averages(...)`
- `build_reference_pose_index(...)`
- `build_segment_comparisons(...)`
- `render_overlay_video(...)`

### `bulgarian/gym_input_ui.py`

Purpose:

- thin desktop wrapper around `run_analysis(...)`

Behavior:

- lets the user pick a video
- creates a unique output folder under `ui_runs/`
- runs analysis on a background thread
- shows summary text
- loops the generated overlay video in the window

### Non-primary files

- `bulgarian/data_bulg.py`
  - scratch or local utility, not the main entrypoint
- `dummies.py`
  - scratch or exploratory code, not the main entrypoint

## Hard invariants

### Pipeline invariants

- The project is single-exercise today.
- The comparison is segment-based, not whole-video-based.
- Reference matching is done by exact `segment_type`.
- Interpolation is fixed to `0..100`, inclusive, one row per integer.
- The UI must write each run into its own timestamped folder.

### Metric invariants

- Interest fields are currently fixed to:
  - `knee_angle_deg`
  - `torso_inclination_abs_deg`
  - `neck_inclination_abs_deg`
- If these change, both the reference builder and input analyzer must change together.

### Feedback invariants

Qualitative labels come from `mean_abs_pct_diff_*`:

- `0-3`: `buen ejercicio`
- `4-8`: `aun se puede mejorar`
- `9-16`: `es necesario ajustar`
- `17-25`: `realizar ajustes profundos`
- `>25`: `riesgo de lesion`

`segment_assessment` must be the worst label among the field-level assessments.

### Versioning invariants

- Keep source code and docs in Git.
- Keep local runtime artifacts out of Git, except the four canonical reference CSVs:
  - videos
  - non-canonical CSVs
  - `.task`
  - images
  - `ui_runs/`

## Change rules

If you change interest fields, also update:

- `gym_try.py`
- `gym_input.py`
- UI summary generation
- docs

If you change segmentation logic, also update:

- reference generation
- segment interpolation
- reference comparison
- overlay assumptions

If you move files or defaults, also update:

- hardcoded default paths
- docs
- any user-facing command examples

## Minimal validation before closing work

Always try to confirm at least this:

- `python -m py_compile gym_try.py`
- `python -m py_compile gym\bulgarian\gym_input.py`
- `python -m py_compile gym\bulgarian\gym_input_ui.py`

If local assets are available, also try:

- rebuild the reference with `gym_try.py`
- run CLI analysis once
- run the UI once

## Common traps

- Missing model or reference CSVs will fail at runtime even if the repo looks clean.
- `gym_try.py` and `gym_input.py` use mixed naming languages.
- A change can look local but still break CSV compatibility.
- `ui_runs/` is a local runtime cache, not a source directory.
