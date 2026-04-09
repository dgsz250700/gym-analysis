# SPEC

LLM-oriented functional specification for the current project.

## Product goal

Build a local pipeline that:

1. processes exercise videos with MediaPipe Pose
2. extracts pose landmarks
3. derives biomechanical variables of interest
4. segments the motion into comparable phases
5. interpolates each phase to a common `0..100` scale
6. builds an average reference from local reference videos
7. compares a new input video against that reference
8. produces quantitative, qualitative, and visual feedback

## Supported scope

Current scope only:

- exercise: Bulgarian Split Squat
- default side: `right`
- optional side: `left`
  - implemented as an argument
  - not fully validated with equivalent local data

Current variables of interest:

- `knee_angle_deg`
- `torso_inclination_abs_deg`
- `neck_inclination_abs_deg`

## Required local inputs

### Reference build inputs

- local reference videos under `gym/bulgarian/`
- local MediaPipe model file

### Input analysis inputs

- one user-selected input video
- reference averages CSV
- reference angles CSV
- reference changes CSV
- MediaPipe model file

Important:

- the model and videos are local-only
- the four canonical reference CSVs are expected to live in Git

## Functional requirements

### FR-1 Pose processing

The system must process video frames with MediaPipe Pose and retain the landmarks needed to derive:

- knee angle
- torso inclination
- neck inclination

### FR-2 Smoothing

The system must smooth pose points and derived angles with EMA before later stages use them.

### FR-3 Change detection

The system must detect direction changes from the knee angle time series.

Canonical event labels:

- `baja_a_sube`
- `sube_a_baja`

### FR-4 Segment creation

The system must build segments between consecutive direction change events.

Canonical segment key:

- `segment_type = start_change_direction|end_change_direction`

### FR-5 Interpolation

Each segment must be interpolated linearly to a normalized timeline:

- domain: `0..100`
- inclusive
- one row per integer percent

### FR-6 Reference generation

The reference pipeline must aggregate interpolated segments by `segment_type` and `normalized_percent`.

Canonical reference outputs:

- `bulgarian_angles.csv`
- `bulgarian_angle_changes.csv`
- `bulgarian_interpolated_segments.csv`
- `bulgarian_segment_averages.csv`

These four reference CSVs are valid versioned artifacts for this repository.

### FR-7 Input analysis

For a new input video, the backend must generate:

- per-frame rows
- change rows
- interpolated segment rows
- segment average rows
- segment comparison rows
- overlay video

Canonical per-video outputs:

- `*_angles.csv`
- `*_angle_changes.csv`
- `*_interpolated_segments.csv`
- `*_segment_averages.csv`
- `*_segment_comparison.csv`
- `*_overlay.mp4`

### FR-8 Segment comparison

The comparison stage must compare each input segment only against the reference rows with the same `segment_type`.

The comparison stage must emit at least:

- `mean_signed_pct_diff_*`
- `mean_abs_pct_diff_*`
- `assessment_*`
- `segment_assessment`

### FR-9 Qualitative assessment

Qualitative labels must be derived from mean absolute percentage difference:

- `0-3`: `buen ejercicio`
- `4-8`: `aun se puede mejorar`
- `9-16`: `es necesario ajustar`
- `17-25`: `realizar ajustes profundos`
- `>25`: `riesgo de lesion`

`segment_assessment` must be the worst label across the field-level assessments.

### FR-10 Overlay rendering

The final overlay video must show:

- input pose in green
- average reference pose in orange
- segment assessment text

The reference pose must be reconstructed from normalized reference landmarks and then re-scaled onto the input body.

### FR-11 UI workflow

The desktop UI must:

- let the user choose a video
- call `run_analysis(...)`
- write outputs into a unique timestamped run folder
- show a text summary
- play the overlay video
- expose the comparison CSV path to the user

## Data and contract invariants

- The project is single-exercise today.
- String labels in CSVs and code remain Spanish.
- `INTEREST_FIELDS` must stay aligned across reference generation and input analysis.
- CSV headers are a cross-file contract and should change only deliberately.
- A missing or renamed `segment_type` breaks comparison.

## Runtime behavior and error expectations

- Missing video, model, or reference CSVs should fail early.
- Unsupported video extensions should fail early.
- If no comparable segments exist, comparison rows may be empty.
- UI output isolation is required to avoid stale-file and file-lock issues.

## Versioning policy

The repository should keep only:

- `.py`
- `.md`
- `.gitignore`
- the four canonical reference CSVs in `gym/bulgarian/`

The repository should not keep:

- videos
- non-canonical CSVs
- `.task`
- images
- `ui_runs/`

## Non-goals

- generalized multi-exercise framework
- dynamic exercise configuration UI
- database persistence
- web API
- training a custom model

## Acceptance criteria for the current state

- reference data can be rebuilt from the local dataset
- one input video can be processed end-to-end
- a segment comparison CSV is produced
- an overlay video is produced
- the UI can trigger analysis and display the generated results
