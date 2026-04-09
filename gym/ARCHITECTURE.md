# ARCHITECTURE

System map for LLMs and future maintainers.

## System boundary

This is a local desktop pipeline, not a service.

It currently consists of:

- one reference-building script
- one input-analysis backend
- one lightweight desktop UI
- local runtime assets that are intentionally not versioned

There is no:

- database
- API server
- background worker
- package or module boundary separating core logic yet

## Path reality

- Actual Git root: `C:\Users\WINDOWS\Documents`
- Logical project root: `C:\Users\WINDOWS\Documents\gym`
- Main reference script still lives outside the logical project root:
  - `C:\Users\WINDOWS\Documents\gym_try.py`

This mismatch is the main structural trap for new agents.

## High-level flow

### Flow 1: build reference

`gym_try.py`

1. load local reference videos
2. run MediaPipe pose detection
3. smooth pose points and angles
4. detect knee direction changes
5. build segments between consecutive events
6. interpolate each segment to `0..100`
7. average rows by `segment_type` and normalized percent
8. write reference CSV artifacts

### Flow 2: analyze one input video

`gym/bulgarian/gym_input.py`

1. validate local input paths
2. process video frames into per-frame rows
3. detect direction changes
4. build interpolated segments
5. build averages for the input video
6. load reference CSVs
7. compare input segments to reference segments
8. build reference pose index for overlay rendering
9. write output CSVs
10. render overlay video
11. return an analysis result dictionary

### Flow 3: UI wrapper

`gym/bulgarian/gym_input_ui.py`

1. ask user for a video path
2. create a unique run folder in `ui_runs/`
3. call `run_analysis(...)` on a background thread
4. show summary text
5. play the generated overlay video in a loop

## Module map

### `gym_try.py`

Role:

- reference generation only

Characteristics:

- mostly Spanish function names
- works directly with local files
- writes reference CSVs expected later by the backend

Important functions:

- `procesar_video(...)`
- `construir_segmentos_interpolados(...)`
- `construir_promedios_segmentos(...)`

### `gym/bulgarian/gym_input.py`

Role:

- primary analysis backend

Sub-responsibilities:

- input validation
- video processing
- segmentation
- interpolation
- averaging
- reference lookup
- comparison
- overlay rendering
- output writing

Important functions by stage:

Input and file resolution:

- `parse_args(...)`
- `choose_video_path(...)`
- `resolve_output_paths(...)`

Frame processing:

- `process_video(...)`
- `calculate_angle(...)`
- `calculate_vertical_inclination(...)`

Segmentation and interpolation:

- `build_segment_definitions(...)`
- `build_interpolated_segments(...)`
- `interpolate_segment(...)`

Aggregation and comparison:

- `build_segment_averages(...)`
- `build_reference_index(...)`
- `build_segment_comparisons(...)`

Overlay:

- `build_reference_pose_index(...)`
- `normalize_pose_points(...)`
- `denormalize_pose_points(...)`
- `render_overlay_video(...)`

Orchestration:

- `run_analysis(...)`

### `gym/bulgarian/gym_input_ui.py`

Role:

- UI wrapper, not business logic owner

Important behavior:

- builds unique output directories
- does not own comparison logic
- does not own segmentation logic
- expects backend return keys and output file structure to stay stable

## Data contracts

### Input video contract

Supported extensions:

- `.mp4`
- `.mov`
- `.avi`
- `.mkv`
- `.m4v`

### Reference artifact contract

The backend expects these local files to exist:

- reference averages CSV
- reference angles CSV
- reference changes CSV
- MediaPipe model `.task`

The four canonical reference CSVs are versioned in Git:

- `gym/bulgarian/bulgarian_angle_changes.csv`
- `gym/bulgarian/bulgarian_angles.csv`
- `gym/bulgarian/bulgarian_interpolated_segments.csv`
- `gym/bulgarian/bulgarian_segment_averages.csv`

Default output path keys returned by `resolve_output_paths(...)`:

- `output_dir`
- `angles`
- `changes`
- `interpolated`
- `averages`
- `comparison`
- `overlay_video`

### `run_analysis(...)` return contract

The backend returns a dictionary with at least:

- `video_path`
- `reference_csv_path`
- `reference_angles_csv_path`
- `reference_changes_csv_path`
- `model_path`
- `output_paths`
- `rows`
- `changes_rows`
- `interpolated_rows`
- `average_rows`
- `comparison_rows`

The UI depends directly on this contract.

## Canonical invariants

- Supported exercise is Bulgarian Split Squat only.
- Default side is `right`.
- Event labels are:
  - `baja_a_sube`
  - `sube_a_baja`
- `segment_type` is always `start_change_direction|end_change_direction`.
- Interpolation target is always `0..100`.
- Comparison is keyed by exact `segment_type`.
- Interest fields are:
  - `knee_angle_deg`
  - `torso_inclination_abs_deg`
  - `neck_inclination_abs_deg`

## Coupling and architectural debt

### Layout coupling

- `gym_try.py` lives outside `gym/`
- Git root is not the logical project root

### Data-contract coupling

- `gym_try.py` and `gym_input.py` share implicit CSV contracts
- there is no shared typed schema or shared constants module yet

### Naming coupling

- reference builder code is mostly Spanish
- analyzer code is mostly English
- data labels remain Spanish

### Runtime asset coupling

- the backend depends on local files not present in Git
- the backend depends on a mix of versioned reference CSVs and non-versioned local assets
- this makes reproduction harder for new agents

## Extension points

Best future seams for refactor:

1. create a shared core module for constants, field names, and math helpers
2. move reference builder under `gym/`
3. separate source, raw data, reference data, and run outputs
4. make exercise configuration explicit instead of hardcoded
5. add automated tests around segmenting, interpolation, comparison, and overlay

## Architectural rule of thumb

Treat this project as:

- source code in Git
- runtime assets local
- CSV schemas as contracts
- UI as a client of `run_analysis(...)`

If a change breaks any of those assumptions, update code and docs together.
