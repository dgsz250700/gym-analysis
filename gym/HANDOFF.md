# HANDOFF

Current handoff for the next agent.

Use this after reading `AGENTS.md`, `ARCHITECTURE.md`, and `SPEC.md`.

## Current snapshot

- Domain: local desktop video analysis for gym technique
- Supported exercise: Bulgarian Split Squat only
- Reference builder: `C:\Users\WINDOWS\Documents\gym_try.py`
- Input analyzer: `C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py`
- UI: `C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input_ui.py`
- Actual Git root: `C:\Users\WINDOWS\Documents`
- Logical project root: `C:\Users\WINDOWS\Documents\gym`

## What is stable today

- per-frame pose processing with MediaPipe
- knee direction change detection
- segment creation between consecutive change events
- interpolation to `0..100`
- segment averaging for the reference dataset
- segment-to-reference percentage comparison
- qualitative assessment labels
- overlay video generation
- a minimal `tkinter` UI that wraps `run_analysis(...)`

## What is intentionally not in Git

The repo is meant to keep source and docs only.

Local runtime artifacts should stay out of version control:

- source videos
- non-canonical generated CSVs
- `.task` model files
- image references
- `ui_runs/`

Canonical reference CSVs that are intentionally kept in Git:

- `gym/bulgarian/bulgarian_angle_changes.csv`
- `gym/bulgarian/bulgarian_angles.csv`
- `gym/bulgarian/bulgarian_interpolated_segments.csv`
- `gym/bulgarian/bulgarian_segment_averages.csv`

Important implication:

- a clean clone may not be runnable until the local model and reference artifacts are present

## Runtime dependencies that another agent must expect

Required local assets:

- input video
- MediaPipe model file, usually `gym/pose_landmarker_full.task`
- reference averages CSV
- reference angles CSV
- reference changes CSV

Default backend expectations:

- `gym/bulgarian/bulgarian_segment_averages.csv`
- `gym/bulgarian/bulgarian_angles.csv`
- `gym/bulgarian/bulgarian_angle_changes.csv`

Additional canonical reference artifact kept in Git:

- `gym/bulgarian/bulgarian_interpolated_segments.csv`

## Architectural decisions already taken

- Comparison is done per segment, not per whole video.
- `segment_type` is the join key between input and reference.
- Qualitative feedback is based on mean absolute percentage difference.
- `segment_assessment` is the worst field-level assessment.
- The overlay reconstructs an average reference pose from normalized pose data, not just angle curves.
- The UI writes each run to a unique timestamped folder to avoid file locking issues.

## Fragile areas

### 1. Project layout

- `gym_try.py` still lives outside `gym/`
- Git root is still above the logical project root
- this is easy for humans and agents to miss

### 2. Reference and input contract

- `gym_try.py` and `gym_input.py` must agree on:
  - event labels
  - `segment_type`
  - interest field names
  - CSV column expectations

### 3. Mixed naming style

- `gym_try.py` is mostly Spanish
- `gym_input.py` is mostly English
- string labels inside the data remain Spanish

### 4. No automated tests

- breakage risk is highest around:
  - segmentation
  - interpolation
  - overlay alignment
  - CSV compatibility

## Symptom-driven debugging

### If the backend raises missing-file errors

Check:

- model path
- reference CSV paths
- whether local assets exist outside Git

### If comparison rows are empty

Check:

- that `process_video(...)` produced direction changes
- that input `segment_type` values match reference `segment_type` values exactly
- that the reference CSV still has the expected headers

### If the overlay looks misaligned

Check:

- `build_reference_pose_index(...)`
- `normalize_pose_points(...)`
- `denormalize_pose_points(...)`
- `render_overlay_video(...)`

### If the UI behaves badly after repeated runs

Check:

- unique `ui_runs/<video>_ui_<timestamp>` output folders
- playback callback cleanup
- that the generated overlay file exists before playback starts

## Highest-value next steps

1. Move `gym_try.py` into `gym/` or extract a shared package used by both pipelines.
2. Extract shared config and constants into a common module.
3. Parameterize exercise-specific settings instead of hardcoding Bulgarian-specific behavior.
4. Separate raw data, reference data, runtime outputs, and source code more clearly.
5. Add automated tests for segmentation, interpolation, feedback classification, and overlay behavior.

## Recommended first actions for a new agent

1. Read `AGENTS.md`, `ARCHITECTURE.md`, and `SPEC.md`.
2. Run `py_compile` on the three active Python entrypoints.
3. Confirm whether local model and reference CSVs are available.
4. Only then attempt runtime debugging or feature work.

## Useful commands

Compile-only sanity check:

```powershell
python -m py_compile C:\Users\WINDOWS\Documents\gym_try.py
python -m py_compile C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py
python -m py_compile C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input_ui.py
```

Rebuild reference:

```powershell
python C:\Users\WINDOWS\Documents\gym_try.py
```

Run CLI analysis:

```powershell
python C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py
```

Run UI:

```powershell
python C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input_ui.py
```
