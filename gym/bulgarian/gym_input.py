import argparse
import csv
import math
from pathlib import Path

import cv2
import mediapipe as mp

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_MODEL_PATH = PROJECT_DIR / "pose_landmarker_full.task"
DEFAULT_REFERENCE_AVERAGES_CSV = SCRIPT_DIR / "bulgarian_segment_averages.csv"
DEFAULT_REFERENCE_ANGLES_CSV = SCRIPT_DIR / "bulgarian_angles.csv"
DEFAULT_REFERENCE_CHANGES_CSV = SCRIPT_DIR / "bulgarian_angle_changes.csv"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

DEFAULT_START_SECOND = 0.0
DEFAULT_SHOW_PREVIEW = False
DEFAULT_SIDE = "right"  # "right" o "left"
ALPHA_POINTS = 0.25
ALPHA_ANGLE = 0.2
MIN_VISIBILITY = 0.6
ANGLE_CHANGE_THRESHOLD = 0.5
MAX_WIDTH = 1000
MAX_HEIGHT = 700
POSE_POINT_NAMES = ("ear", "shoulder", "hip", "knee", "ankle")
POSE_CONNECTIONS = (
    ("ear", "shoulder"),
    ("shoulder", "hip"),
    ("hip", "knee"),
    ("knee", "ankle"),
)
INPUT_POSE_COLOR = (0, 255, 0)
REFERENCE_POSE_COLOR = (0, 165, 255)
TEXT_COLOR = (255, 255, 255)

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

FIELDNAMES = [
    "video_name",
    "frame",
    "tiempo_ms",
    "landmarks_confiables",
    "ear_x",
    "ear_y",
    "shoulder_x",
    "shoulder_y",
    "hip_x",
    "hip_y",
    "knee_x",
    "knee_y",
    "ankle_x",
    "ankle_y",
    "knee_angle_deg",
    "torso_inclination_signed_deg",
    "torso_inclination_abs_deg",
    "neck_inclination_signed_deg",
    "neck_inclination_abs_deg",
]

CHANGE_FIELDNAMES = [
    "video_name",
    "frame_cambio",
    "tiempo_ms",
    "knee_angle_deg",
    "delta_previo_deg",
    "delta_actual_deg",
    "cambio_direccion",
]

INTEREST_FIELDS = [
    "knee_angle_deg",
    "torso_inclination_abs_deg",
    "neck_inclination_abs_deg",
]

INTERPOLATED_FIELDNAMES = [
    "video_name",
    "segment_id",
    "segment_type",
    "start_change_direction",
    "end_change_direction",
    "start_frame",
    "end_frame",
    "start_tiempo_ms",
    "end_tiempo_ms",
    "segment_frame_count",
    "segment_valid_frame_count",
    "normalized_percent",
    *INTEREST_FIELDS,
]

AVERAGE_FIELDNAMES = [
    "segment_type",
    "start_change_direction",
    "end_change_direction",
    "normalized_percent",
    "segment_count",
    *[f"avg_{field_name}" for field_name in INTEREST_FIELDS],
]

COMPARISON_FIELDNAMES = [
    "video_name",
    "segment_id",
    "segment_type",
    "start_change_direction",
    "end_change_direction",
    "reference_found",
    "reference_segment_count",
    *[f"compared_points_{field_name}" for field_name in INTEREST_FIELDS],
    *[f"mean_signed_pct_diff_{field_name}" for field_name in INTEREST_FIELDS],
    *[f"mean_abs_pct_diff_{field_name}" for field_name in INTEREST_FIELDS],
    *[f"assessment_{field_name}" for field_name in INTEREST_FIELDS],
    "segment_assessment",
]


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Procesa un video con MediaPipe, segmenta entre cambios de direccion, "
            "interpola las variables de interes y compara cada segmento con la referencia."
        )
    )
    parser.add_argument(
        "video",
        nargs="?",
        help="Ruta del video a analizar. Si no se indica, se intenta abrir un selector.",
    )
    parser.add_argument(
        "--reference-averages",
        default=str(DEFAULT_REFERENCE_AVERAGES_CSV),
        help="CSV de referencia generado previamente con gym_try.py.",
    )
    parser.add_argument(
        "--reference-angles",
        default=str(DEFAULT_REFERENCE_ANGLES_CSV),
        help="CSV de angulos/landmarks de referencia generado con gym_try.py.",
    )
    parser.add_argument(
        "--reference-changes",
        default=str(DEFAULT_REFERENCE_CHANGES_CSV),
        help="CSV de cambios de direccion de referencia generado con gym_try.py.",
    )
    parser.add_argument(
        "--model",
        default=str(DEFAULT_MODEL_PATH),
        help="Ruta al modelo .task de MediaPipe.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Carpeta donde se guardaran los CSV de salida. Por defecto usa la carpeta del video.",
    )
    parser.add_argument(
        "--start-second",
        type=float,
        default=DEFAULT_START_SECOND,
        help="Segundo inicial desde el que se procesara el video.",
    )
    parser.add_argument(
        "--side",
        choices=("left", "right"),
        default=DEFAULT_SIDE,
        help="Lado del cuerpo que se analizara.",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        default=DEFAULT_SHOW_PREVIEW,
        help="Muestra una ventana de previsualizacion durante el analisis.",
    )
    return parser.parse_args()


def ema(actual, previous, alpha):
    if previous is None:
        return actual
    return alpha * actual + (1 - alpha) * previous


def ema_point(actual, previous, alpha):
    if previous is None:
        return actual
    return (
        ema(actual[0], previous[0], alpha),
        ema(actual[1], previous[1], alpha),
    )


def calculate_angle(a, b, c):
    ab = (a[0] - b[0], a[1] - b[1])
    cb = (c[0] - b[0], c[1] - b[1])

    mag_ab = math.hypot(ab[0], ab[1])
    mag_cb = math.hypot(cb[0], cb[1])
    if mag_ab == 0 or mag_cb == 0:
        return None

    cos_theta = (ab[0] * cb[0] + ab[1] * cb[1]) / (mag_ab * mag_cb)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return math.degrees(math.acos(cos_theta))


def calculate_vertical_inclination(top_point, bottom_point):
    dx = top_point[0] - bottom_point[0]
    dy = top_point[1] - bottom_point[1]
    if dx == 0 and dy == 0:
        return None, None

    signed_angle = math.degrees(math.atan2(dx, -dy))
    return signed_angle, abs(signed_angle)


def get_indices(side):
    if side == "left":
        return 7, 11, 23, 25, 27
    return 8, 12, 24, 26, 28


def create_base_row(video_path, frame_idx, timestamp_ms):
    return {
        "video_name": video_path.name,
        "frame": frame_idx,
        "tiempo_ms": timestamp_ms,
        "landmarks_confiables": False,
        "ear_x": None,
        "ear_y": None,
        "shoulder_x": None,
        "shoulder_y": None,
        "hip_x": None,
        "hip_y": None,
        "knee_x": None,
        "knee_y": None,
        "ankle_x": None,
        "ankle_y": None,
        "knee_angle_deg": None,
        "torso_inclination_signed_deg": None,
        "torso_inclination_abs_deg": None,
        "neck_inclination_signed_deg": None,
        "neck_inclination_abs_deg": None,
    }


def normalize_direction_change(change_direction):
    if change_direction in {"baja_a_sube", "sube_a_baja"}:
        return change_direction
    return None


def parse_optional_float(value):
    if value in (None, ""):
        return None
    return float(value)


def classify_difference(abs_diff_pct):
    if abs_diff_pct is None:
        return None
    if abs_diff_pct <= 3:
        return "buen ejercicio"
    if abs_diff_pct <= 8:
        return "aun se puede mejorar"
    if abs_diff_pct <= 16:
        return "es necesario ajustar"
    if abs_diff_pct <= 25:
        return "realizar ajustes profundos"
    return "riesgo de lesion"


def assessment_priority(label):
    priority_map = {
        "buen ejercicio": 0,
        "aun se puede mejorar": 1,
        "es necesario ajustar": 2,
        "realizar ajustes profundos": 3,
        "riesgo de lesion": 4,
    }
    return priority_map.get(label, -1)


def choose_video_path(cli_video_path):
    if cli_video_path:
        return Path(cli_video_path).expanduser()

    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected_path = filedialog.askopenfilename(
            title="Selecciona el video a analizar",
            filetypes=[
                ("Videos", "*.mp4 *.mov *.avi *.mkv *.m4v"),
                ("Todos los archivos", "*.*"),
            ],
        )
        root.destroy()
        if selected_path:
            return Path(selected_path)
    except Exception as exc:
        print(f"No se pudo abrir el selector de archivos: {exc}")

    typed_path = input("Ruta del video a analizar: ").strip().strip('\"')
    if not typed_path:
        raise FileNotFoundError("No se selecciono ningun video.")
    return Path(typed_path).expanduser()


def resolve_output_paths(video_path, output_dir):
    if output_dir is None:
        base_output_dir = video_path.parent
    else:
        base_output_dir = Path(output_dir).expanduser()

    base_output_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem
    return {
        "output_dir": base_output_dir,
        "angles": base_output_dir / f"{stem}_angles.csv",
        "changes": base_output_dir / f"{stem}_angle_changes.csv",
        "interpolated": base_output_dir / f"{stem}_interpolated_segments.csv",
        "averages": base_output_dir / f"{stem}_segment_averages.csv",
        "comparison": base_output_dir / f"{stem}_segment_comparison.csv",
        "overlay_video": base_output_dir / f"{stem}_overlay.mp4",
    }


def write_rows_to_csv(csv_path, fieldnames, rows):
    with open(csv_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_rows_from_csv(csv_path):
    with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def point_distance(point_a, point_b):
    if point_a is None or point_b is None:
        return None
    return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


def extract_pose_points(row):
    pose_points = {}

    for point_name in POSE_POINT_NAMES:
        x = parse_optional_float(row.get(f"{point_name}_x"))
        y = parse_optional_float(row.get(f"{point_name}_y"))
        if x is None or y is None:
            pose_points[point_name] = None
        else:
            pose_points[point_name] = (x, y)

    return pose_points


def compute_pose_scale(pose_points):
    torso_length = point_distance(pose_points.get("hip"), pose_points.get("shoulder"))
    thigh_length = point_distance(pose_points.get("hip"), pose_points.get("knee"))
    shin_length = point_distance(pose_points.get("knee"), pose_points.get("ankle"))

    if torso_length is None or thigh_length is None or shin_length is None:
        return None

    pose_scale = torso_length + thigh_length + shin_length
    if pose_scale <= 0:
        return None
    return pose_scale


def normalize_pose_points(pose_points):
    hip_point = pose_points.get("hip")
    pose_scale = compute_pose_scale(pose_points)
    if hip_point is None or pose_scale is None:
        return None

    normalized_points = {}

    for point_name in POSE_POINT_NAMES:
        point = pose_points.get(point_name)
        if point is None:
            normalized_points[point_name] = None
        else:
            normalized_points[point_name] = (
                (point[0] - hip_point[0]) / pose_scale,
                (point[1] - hip_point[1]) / pose_scale,
            )

    return normalized_points


def denormalize_pose_points(relative_points, hip_point, pose_scale):
    if relative_points is None or hip_point is None or pose_scale in (None, 0):
        return None

    pose_points = {}

    for point_name in POSE_POINT_NAMES:
        relative_point = relative_points.get(point_name)
        if relative_point is None:
            pose_points[point_name] = None
        else:
            pose_points[point_name] = (
                hip_point[0] + relative_point[0] * pose_scale,
                hip_point[1] + relative_point[1] * pose_scale,
            )

    return pose_points


def compute_normalized_percent(frame_idx, start_frame, end_frame):
    if end_frame <= start_frame:
        return 0
    normalized_percent = round(((frame_idx - start_frame) / (end_frame - start_frame)) * 100)
    return max(0, min(100, int(normalized_percent)))


def interpolate_linear_values(xs, ys, target_xs):
    if not xs or not ys:
        return [None for _ in target_xs]

    if len(xs) == 1:
        return [round(ys[0], 2) for _ in target_xs]

    results = []
    index = 0

    for target_x in target_xs:
        if target_x <= xs[0]:
            results.append(round(ys[0], 2))
            continue

        if target_x >= xs[-1]:
            results.append(round(ys[-1], 2))
            continue

        while index + 1 < len(xs) and xs[index + 1] < target_x:
            index += 1

        x0 = xs[index]
        x1 = xs[index + 1]
        y0 = ys[index]
        y1 = ys[index + 1]

        if x1 == x0:
            value = y1
        else:
            ratio = (target_x - x0) / (x1 - x0)
            value = y0 + (y1 - y0) * ratio

        results.append(round(value, 2))

    return results


def interpolate_segment(segment_rows, start_frame, end_frame, field_name):
    frame_span = end_frame - start_frame
    xs = []
    ys = []

    for row in segment_rows:
        value = row.get(field_name)
        if value is None:
            continue

        if frame_span == 0:
            normalized_position = 0.0
        else:
            normalized_position = ((row["frame"] - start_frame) / frame_span) * 100

        xs.append(normalized_position)
        ys.append(value)

    return interpolate_linear_values(xs, ys, list(range(101)))


def build_segment_definitions(changes_rows):
    segmentation_events = []

    for change in changes_rows:
        change_direction = normalize_direction_change(change["cambio_direccion"])
        if change_direction is None:
            continue

        segmentation_events.append(
            {
                "frame": int(change["frame_cambio"]),
                "tiempo_ms": int(change["tiempo_ms"]),
                "change_direction": change_direction,
            }
        )

    if len(segmentation_events) < 2:
        return []

    segmentation_events.sort(key=lambda event: event["frame"])
    segment_definitions = []

    for segment_id, (start_event, end_event) in enumerate(
        zip(segmentation_events, segmentation_events[1:]),
        start=1,
    ):
        if end_event["frame"] <= start_event["frame"]:
            continue

        segment_definitions.append(
            {
                "segment_id": segment_id,
                "segment_type": f"{start_event['change_direction']}|{end_event['change_direction']}",
                "start_change_direction": start_event["change_direction"],
                "end_change_direction": end_event["change_direction"],
                "start_frame": start_event["frame"],
                "end_frame": end_event["frame"],
                "start_tiempo_ms": start_event["tiempo_ms"],
                "end_tiempo_ms": end_event["tiempo_ms"],
            }
        )

    return segment_definitions


def build_interpolated_segments(video_path, rows, changes_rows):
    segment_definitions = build_segment_definitions(changes_rows)
    if not segment_definitions:
        return []

    reliable_rows = [row for row in rows if row["landmarks_confiables"]]
    interpolated_rows = []

    for segment in segment_definitions:
        segment_rows = [
            row
            for row in reliable_rows
            if segment["start_frame"] <= row["frame"] <= segment["end_frame"]
        ]

        if not segment_rows:
            continue

        interpolations = {
            field_name: interpolate_segment(
                segment_rows,
                segment["start_frame"],
                segment["end_frame"],
                field_name,
            )
            for field_name in INTEREST_FIELDS
        }

        segment_frame_count = segment["end_frame"] - segment["start_frame"] + 1
        segment_valid_frame_count = len(segment_rows)

        for normalized_percent in range(101):
            interpolated_row = {
                "video_name": video_path.name,
                "segment_id": segment["segment_id"],
                "segment_type": segment["segment_type"],
                "start_change_direction": segment["start_change_direction"],
                "end_change_direction": segment["end_change_direction"],
                "start_frame": segment["start_frame"],
                "end_frame": segment["end_frame"],
                "start_tiempo_ms": segment["start_tiempo_ms"],
                "end_tiempo_ms": segment["end_tiempo_ms"],
                "segment_frame_count": segment_frame_count,
                "segment_valid_frame_count": segment_valid_frame_count,
                "normalized_percent": normalized_percent,
            }

            for field_name in INTEREST_FIELDS:
                interpolated_row[field_name] = interpolations[field_name][normalized_percent]

            interpolated_rows.append(interpolated_row)

    return interpolated_rows


def build_segment_averages(interpolated_rows):
    if not interpolated_rows:
        return []

    accumulators = {}

    for row in interpolated_rows:
        normalized_percent = int(row["normalized_percent"])
        group_key = (
            row["segment_type"],
            row["start_change_direction"],
            row["end_change_direction"],
            normalized_percent,
        )

        if group_key not in accumulators:
            accumulators[group_key] = {
                "segment_ids": set(),
                "sums": {field_name: 0.0 for field_name in INTEREST_FIELDS},
                "counts": {field_name: 0 for field_name in INTEREST_FIELDS},
            }

        accumulator = accumulators[group_key]
        accumulator["segment_ids"].add((row["video_name"], row["segment_id"]))

        for field_name in INTEREST_FIELDS:
            value = parse_optional_float(row.get(field_name))
            if value is None:
                continue
            accumulator["sums"][field_name] += value
            accumulator["counts"][field_name] += 1

    average_rows = []

    for group_key in sorted(accumulators, key=lambda key: (key[0], key[3])):
        segment_type, start_change_direction, end_change_direction, normalized_percent = group_key
        accumulator = accumulators[group_key]
        average_row = {
            "segment_type": segment_type,
            "start_change_direction": start_change_direction,
            "end_change_direction": end_change_direction,
            "normalized_percent": normalized_percent,
            "segment_count": len(accumulator["segment_ids"]),
        }

        for field_name in INTEREST_FIELDS:
            count = accumulator["counts"][field_name]
            if count == 0:
                average_row[f"avg_{field_name}"] = None
            else:
                average_row[f"avg_{field_name}"] = round(accumulator["sums"][field_name] / count, 2)

        average_rows.append(average_row)

    return average_rows


def convert_reference_angle_row(row):
    converted_row = {
        "video_name": row["video_name"],
        "frame": int(float(row["frame"])),
        "tiempo_ms": int(float(row["tiempo_ms"])),
        "landmarks_confiables": str(row["landmarks_confiables"]).strip().lower() == "true",
    }

    for field_name in FIELDNAMES:
        if field_name in {"video_name", "frame", "tiempo_ms", "landmarks_confiables"}:
            continue
        converted_row[field_name] = parse_optional_float(row.get(field_name))

    return converted_row


def convert_reference_change_row(row):
    return {
        "video_name": row["video_name"],
        "frame_cambio": int(float(row["frame_cambio"])),
        "tiempo_ms": int(float(row["tiempo_ms"])),
        "knee_angle_deg": parse_optional_float(row.get("knee_angle_deg")),
        "delta_previo_deg": parse_optional_float(row.get("delta_previo_deg")),
        "delta_actual_deg": parse_optional_float(row.get("delta_actual_deg")),
        "cambio_direccion": row["cambio_direccion"],
    }


def interpolate_reference_pose_segment(segment_rows, start_frame, end_frame):
    field_series = {
        f"{point_name}_{axis}": {"xs": [], "ys": []}
        for point_name in POSE_POINT_NAMES
        for axis in ("rel_x", "rel_y")
    }

    for row in segment_rows:
        pose_points = extract_pose_points(row)
        normalized_pose_points = normalize_pose_points(pose_points)
        if normalized_pose_points is None:
            continue

        normalized_percent = compute_normalized_percent(row["frame"], start_frame, end_frame)

        for point_name in POSE_POINT_NAMES:
            normalized_point = normalized_pose_points.get(point_name)
            if normalized_point is None:
                continue

            field_series[f"{point_name}_rel_x"]["xs"].append(normalized_percent)
            field_series[f"{point_name}_rel_x"]["ys"].append(normalized_point[0])
            field_series[f"{point_name}_rel_y"]["xs"].append(normalized_percent)
            field_series[f"{point_name}_rel_y"]["ys"].append(normalized_point[1])

    interpolated_fields = {}
    target_xs = list(range(101))

    for field_name, series in field_series.items():
        interpolated_fields[field_name] = interpolate_linear_values(
            series["xs"],
            series["ys"],
            target_xs,
        )

    interpolated_points = {}

    for normalized_percent in range(101):
        interpolated_points[normalized_percent] = {}

        for point_name in POSE_POINT_NAMES:
            rel_x = interpolated_fields[f"{point_name}_rel_x"][normalized_percent]
            rel_y = interpolated_fields[f"{point_name}_rel_y"][normalized_percent]
            if rel_x is None or rel_y is None:
                interpolated_points[normalized_percent][point_name] = None
            else:
                interpolated_points[normalized_percent][point_name] = (rel_x, rel_y)

    return interpolated_points


def build_reference_pose_index(reference_angle_rows, reference_change_rows):
    rows_by_video = {}
    changes_by_video = {}

    for row in reference_angle_rows:
        converted_row = convert_reference_angle_row(row)
        rows_by_video.setdefault(converted_row["video_name"], []).append(converted_row)

    for row in reference_change_rows:
        converted_row = convert_reference_change_row(row)
        changes_by_video.setdefault(converted_row["video_name"], []).append(converted_row)

    accumulators = {}

    for video_name, rows in rows_by_video.items():
        segment_definitions = build_segment_definitions(changes_by_video.get(video_name, []))
        if not segment_definitions:
            continue

        reliable_rows = [row for row in rows if row["landmarks_confiables"]]

        for segment in segment_definitions:
            segment_rows = [
                row
                for row in reliable_rows
                if segment["start_frame"] <= row["frame"] <= segment["end_frame"]
            ]

            if not segment_rows:
                continue

            interpolated_points = interpolate_reference_pose_segment(
                segment_rows,
                segment["start_frame"],
                segment["end_frame"],
            )

            for normalized_percent, pose_points in interpolated_points.items():
                group_key = (
                    segment["segment_type"],
                    segment["start_change_direction"],
                    segment["end_change_direction"],
                    normalized_percent,
                )

                if group_key not in accumulators:
                    accumulators[group_key] = {
                        "counts": {
                            point_name: {"x": 0, "y": 0}
                            for point_name in POSE_POINT_NAMES
                        },
                        "sums": {
                            point_name: {"x": 0.0, "y": 0.0}
                            for point_name in POSE_POINT_NAMES
                        },
                    }

                accumulator = accumulators[group_key]

                for point_name in POSE_POINT_NAMES:
                    point = pose_points.get(point_name)
                    if point is None:
                        continue

                    accumulator["sums"][point_name]["x"] += point[0]
                    accumulator["sums"][point_name]["y"] += point[1]
                    accumulator["counts"][point_name]["x"] += 1
                    accumulator["counts"][point_name]["y"] += 1

    reference_pose_index = {}

    for group_key in sorted(accumulators, key=lambda key: (key[0], key[3])):
        segment_type, start_change_direction, end_change_direction, normalized_percent = group_key
        accumulator = accumulators[group_key]

        if segment_type not in reference_pose_index:
            reference_pose_index[segment_type] = {
                "start_change_direction": start_change_direction,
                "end_change_direction": end_change_direction,
                "points": {},
            }

        reference_pose_index[segment_type]["points"][normalized_percent] = {}

        for point_name in POSE_POINT_NAMES:
            count_x = accumulator["counts"][point_name]["x"]
            count_y = accumulator["counts"][point_name]["y"]
            if count_x == 0 or count_y == 0:
                reference_pose_index[segment_type]["points"][normalized_percent][point_name] = None
            else:
                reference_pose_index[segment_type]["points"][normalized_percent][point_name] = (
                    accumulator["sums"][point_name]["x"] / count_x,
                    accumulator["sums"][point_name]["y"] / count_y,
                )

    return reference_pose_index


def build_reference_index(reference_rows):
    reference_index = {}

    for row in reference_rows:
        segment_type = row["segment_type"]
        normalized_percent = int(row["normalized_percent"])

        if segment_type not in reference_index:
            reference_index[segment_type] = {
                "start_change_direction": row["start_change_direction"],
                "end_change_direction": row["end_change_direction"],
                "segment_count": int(row["segment_count"]),
                "points": {},
            }

        reference_index[segment_type]["points"][normalized_percent] = row

    return reference_index


def build_segment_comparisons(interpolated_rows, reference_rows):
    if not interpolated_rows:
        return []

    reference_index = build_reference_index(reference_rows)
    segments = {}

    for row in interpolated_rows:
        segment_key = (
            row["video_name"],
            int(row["segment_id"]),
            row["segment_type"],
            row["start_change_direction"],
            row["end_change_direction"],
        )
        segments.setdefault(segment_key, []).append(row)

    comparison_rows = []

    for segment_key in sorted(segments, key=lambda key: (key[0], key[1])):
        video_name, segment_id, segment_type, start_change_direction, end_change_direction = segment_key
        reference = reference_index.get(segment_type)
        comparison_row = {
            "video_name": video_name,
            "segment_id": segment_id,
            "segment_type": segment_type,
            "start_change_direction": start_change_direction,
            "end_change_direction": end_change_direction,
            "reference_found": reference is not None,
            "reference_segment_count": reference["segment_count"] if reference is not None else None,
        }
        segment_assessments = []

        for field_name in INTEREST_FIELDS:
            compared_points = 0
            signed_diff_sum = 0.0
            abs_diff_sum = 0.0

            if reference is not None:
                for row in sorted(segments[segment_key], key=lambda item: int(item["normalized_percent"])):
                    normalized_percent = int(row["normalized_percent"])
                    reference_row = reference["points"].get(normalized_percent)
                    if reference_row is None:
                        continue

                    segment_value = parse_optional_float(row.get(field_name))
                    reference_value = parse_optional_float(reference_row.get(f"avg_{field_name}"))
                    if segment_value is None or reference_value in (None, 0.0):
                        continue

                    diff_pct = ((segment_value - reference_value) / reference_value) * 100
                    signed_diff_sum += diff_pct
                    abs_diff_sum += abs(diff_pct)
                    compared_points += 1

            comparison_row[f"compared_points_{field_name}"] = compared_points

            if compared_points == 0:
                comparison_row[f"mean_signed_pct_diff_{field_name}"] = None
                comparison_row[f"mean_abs_pct_diff_{field_name}"] = None
                comparison_row[f"assessment_{field_name}"] = None
            else:
                comparison_row[f"mean_signed_pct_diff_{field_name}"] = round(
                    signed_diff_sum / compared_points,
                    2,
                )
                comparison_row[f"mean_abs_pct_diff_{field_name}"] = round(
                    abs_diff_sum / compared_points,
                    2,
                )
                comparison_row[f"assessment_{field_name}"] = classify_difference(
                    comparison_row[f"mean_abs_pct_diff_{field_name}"]
                )
                segment_assessments.append(comparison_row[f"assessment_{field_name}"])

        if segment_assessments:
            comparison_row["segment_assessment"] = max(
                segment_assessments,
                key=assessment_priority,
            )
        else:
            comparison_row["segment_assessment"] = None

        comparison_rows.append(comparison_row)

    return comparison_rows


def print_comparison_summary(comparison_rows):
    if not comparison_rows:
        print("No se encontraron segmentos para comparar.")
        return

    print("\nComparacion porcentual por segmento:")

    for row in comparison_rows:
        print(f"\nSegmento {row['segment_id']} ({row['segment_type']}):")

        if not row["reference_found"]:
            print("  Sin referencia compatible para este tipo de segmento.")
            continue

        if row["segment_assessment"] is not None:
            print(f"  Evaluacion general: {row['segment_assessment']}")

        for field_name in INTEREST_FIELDS:
            signed_diff = row[f"mean_signed_pct_diff_{field_name}"]
            abs_diff = row[f"mean_abs_pct_diff_{field_name}"]
            compared_points = row[f"compared_points_{field_name}"]
            assessment = row[f"assessment_{field_name}"]

            if signed_diff is None:
                print(f"  {field_name}: sin puntos comparables.")
                continue

            sign_prefix = "+" if signed_diff > 0 else ""
            print(
                f"  {field_name}: {sign_prefix}{signed_diff:.2f}% "
                f"(abs {abs_diff:.2f}%, {compared_points} puntos, {assessment})"
            )


def draw_pose(frame, pose_points, color, radius=6, thickness=3):
    if not pose_points:
        return

    for start_point_name, end_point_name in POSE_CONNECTIONS:
        start_point = pose_points.get(start_point_name)
        end_point = pose_points.get(end_point_name)
        if start_point is None or end_point is None:
            continue
        cv2.line(
            frame,
            tuple(map(int, start_point)),
            tuple(map(int, end_point)),
            color,
            thickness,
        )

    for point_name in POSE_POINT_NAMES:
        point = pose_points.get(point_name)
        if point is None:
            continue
        cv2.circle(frame, tuple(map(int, point)), radius, color, -1)


def draw_overlay_legend(frame):
    cv2.putText(
        frame,
        "Verde: input",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        INPUT_POSE_COLOR,
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Naranja: promedio",
        (20, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        REFERENCE_POSE_COLOR,
        2,
        cv2.LINE_AA,
    )


def render_overlay_video(
    video_path,
    output_video_path,
    rows,
    changes_rows,
    comparison_rows,
    reference_pose_index,
    start_second,
):
    row_by_frame = {int(row["frame"]): row for row in rows}
    segment_definitions = build_segment_definitions(changes_rows)
    comparison_index = {
        (int(row["segment_id"]), row["segment_type"]): row
        for row in comparison_rows
    }

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video para dibujar overlays: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.set(cv2.CAP_PROP_POS_MSEC, start_second * 1000)

    writer = cv2.VideoWriter(
        str(output_video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (frame_width, frame_height),
    )

    current_segment_index = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        row = row_by_frame.get(frame_idx)
        current_pose_points = None
        current_segment = None

        while (
            current_segment_index < len(segment_definitions)
            and frame_idx > segment_definitions[current_segment_index]["end_frame"]
        ):
            current_segment_index += 1

        if (
            current_segment_index < len(segment_definitions)
            and segment_definitions[current_segment_index]["start_frame"] <= frame_idx
            <= segment_definitions[current_segment_index]["end_frame"]
        ):
            current_segment = segment_definitions[current_segment_index]

        if row is not None and row["landmarks_confiables"]:
            current_pose_points = extract_pose_points(row)
            draw_pose(frame, current_pose_points, INPUT_POSE_COLOR, radius=6, thickness=3)

        if current_segment is not None and current_pose_points is not None:
            normalized_percent = compute_normalized_percent(
                frame_idx,
                current_segment["start_frame"],
                current_segment["end_frame"],
            )
            reference_segment = reference_pose_index.get(current_segment["segment_type"])

            if reference_segment is not None:
                relative_reference_points = reference_segment["points"].get(normalized_percent)
                hip_point = current_pose_points.get("hip")
                pose_scale = compute_pose_scale(current_pose_points)
                reference_pose_points = denormalize_pose_points(
                    relative_reference_points,
                    hip_point,
                    pose_scale,
                )
                draw_pose(frame, reference_pose_points, REFERENCE_POSE_COLOR, radius=5, thickness=2)

            comparison_row = comparison_index.get(
                (current_segment["segment_id"], current_segment["segment_type"])
            )
            if comparison_row is not None:
                cv2.putText(
                    frame,
                    f"Segmento {current_segment['segment_id']}: {comparison_row['segment_assessment']}",
                    (20, 92),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    TEXT_COLOR,
                    2,
                    cv2.LINE_AA,
                )

        draw_overlay_legend(frame)
        writer.write(frame)

    writer.release()
    cap.release()


def process_video(video_path, model_path, side, start_second, show_preview):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30

    cap.set(cv2.CAP_PROP_POS_MSEC, start_second * 1000)

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    ear_idx, shoulder_idx, hip_idx, knee_idx, ankle_idx = get_indices(side)
    smoothed_points = {"ear": None, "shoulder": None, "hip": None, "knee": None, "ankle": None}
    knee_angle_smoothed = None
    torso_angle_smoothed = None
    neck_angle_smoothed = None
    saved_rows = []
    saved_changes = []
    previous_knee_angle = None
    previous_angle_frame = None
    previous_angle_timestamp = None
    previous_direction = None
    previous_delta = None

    with PoseLandmarker.create_from_options(options) as landmarker:
        if show_preview:
            cv2.namedWindow("Analisis", cv2.WINDOW_NORMAL)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            timestamp_ms = int((frame_idx / fps) * 1000)
            row = create_base_row(video_path, frame_idx, timestamp_ms)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                frame_height, frame_width = frame.shape[:2]

                ear_lm = landmarks[ear_idx]
                shoulder_lm = landmarks[shoulder_idx]
                hip_lm = landmarks[hip_idx]
                knee_lm = landmarks[knee_idx]
                ankle_lm = landmarks[ankle_idx]

                visibility_ok = (
                    shoulder_lm.visibility >= MIN_VISIBILITY
                    and hip_lm.visibility >= MIN_VISIBILITY
                    and knee_lm.visibility >= MIN_VISIBILITY
                    and ankle_lm.visibility >= MIN_VISIBILITY
                )

                if visibility_ok:
                    shoulder = (shoulder_lm.x * frame_width, shoulder_lm.y * frame_height)
                    hip = (hip_lm.x * frame_width, hip_lm.y * frame_height)
                    knee = (knee_lm.x * frame_width, knee_lm.y * frame_height)
                    ankle = (ankle_lm.x * frame_width, ankle_lm.y * frame_height)

                    smoothed_points["shoulder"] = ema_point(shoulder, smoothed_points["shoulder"], ALPHA_POINTS)
                    smoothed_points["hip"] = ema_point(hip, smoothed_points["hip"], ALPHA_POINTS)
                    smoothed_points["knee"] = ema_point(knee, smoothed_points["knee"], ALPHA_POINTS)
                    smoothed_points["ankle"] = ema_point(ankle, smoothed_points["ankle"], ALPHA_POINTS)

                    knee_angle_current = calculate_angle(
                        smoothed_points["hip"],
                        smoothed_points["knee"],
                        smoothed_points["ankle"],
                    )
                    if knee_angle_current is not None:
                        knee_angle_smoothed = ema(knee_angle_current, knee_angle_smoothed, ALPHA_ANGLE)

                    torso_angle_current, _ = calculate_vertical_inclination(
                        smoothed_points["shoulder"],
                        smoothed_points["hip"],
                    )
                    if torso_angle_current is not None:
                        torso_angle_smoothed = ema(torso_angle_current, torso_angle_smoothed, ALPHA_ANGLE)

                    neck_angle_current = None
                    if ear_lm.visibility >= MIN_VISIBILITY:
                        ear = (ear_lm.x * frame_width, ear_lm.y * frame_height)
                        smoothed_points["ear"] = ema_point(ear, smoothed_points["ear"], ALPHA_POINTS)
                        neck_angle_current, _ = calculate_vertical_inclination(
                            smoothed_points["ear"],
                            smoothed_points["shoulder"],
                        )

                    if neck_angle_current is not None:
                        neck_angle_smoothed = ema(neck_angle_current, neck_angle_smoothed, ALPHA_ANGLE)

                    row.update(
                        {
                            "landmarks_confiables": True,
                            "ear_x": round(smoothed_points["ear"][0], 2) if smoothed_points["ear"] is not None else None,
                            "ear_y": round(smoothed_points["ear"][1], 2) if smoothed_points["ear"] is not None else None,
                            "shoulder_x": round(smoothed_points["shoulder"][0], 2),
                            "shoulder_y": round(smoothed_points["shoulder"][1], 2),
                            "hip_x": round(smoothed_points["hip"][0], 2),
                            "hip_y": round(smoothed_points["hip"][1], 2),
                            "knee_x": round(smoothed_points["knee"][0], 2),
                            "knee_y": round(smoothed_points["knee"][1], 2),
                            "ankle_x": round(smoothed_points["ankle"][0], 2),
                            "ankle_y": round(smoothed_points["ankle"][1], 2),
                            "knee_angle_deg": round(knee_angle_smoothed, 2) if knee_angle_smoothed is not None else None,
                            "torso_inclination_signed_deg": round(torso_angle_smoothed, 2) if torso_angle_smoothed is not None else None,
                            "torso_inclination_abs_deg": round(abs(torso_angle_smoothed), 2) if torso_angle_smoothed is not None else None,
                            "neck_inclination_signed_deg": round(neck_angle_smoothed, 2) if neck_angle_smoothed is not None else None,
                            "neck_inclination_abs_deg": round(abs(neck_angle_smoothed), 2) if neck_angle_smoothed is not None else None,
                        }
                    )

                    if knee_angle_smoothed is not None:
                        if previous_knee_angle is not None:
                            delta_current = knee_angle_smoothed - previous_knee_angle

                            if abs(delta_current) >= ANGLE_CHANGE_THRESHOLD:
                                current_direction = "sube" if delta_current > 0 else "baja"

                                if (
                                    previous_direction is not None
                                    and current_direction != previous_direction
                                    and previous_angle_frame is not None
                                ):
                                    saved_changes.append(
                                        {
                                            "video_name": video_path.name,
                                            "frame_cambio": previous_angle_frame,
                                            "tiempo_ms": previous_angle_timestamp,
                                            "knee_angle_deg": round(previous_knee_angle, 2),
                                            "delta_previo_deg": round(previous_delta, 2) if previous_delta is not None else None,
                                            "delta_actual_deg": round(delta_current, 2),
                                            "cambio_direccion": f"{previous_direction}_a_{current_direction}",
                                        }
                                    )

                                previous_direction = current_direction
                                previous_delta = delta_current

                        previous_knee_angle = knee_angle_smoothed
                        previous_angle_frame = frame_idx
                        previous_angle_timestamp = timestamp_ms

                    if show_preview:
                        shoulder_draw = tuple(map(int, smoothed_points["shoulder"]))
                        hip_draw = tuple(map(int, smoothed_points["hip"]))
                        knee_draw = tuple(map(int, smoothed_points["knee"]))
                        ankle_draw = tuple(map(int, smoothed_points["ankle"]))
                        cv2.line(frame, shoulder_draw, hip_draw, (0, 180, 255), 3)
                        cv2.line(frame, hip_draw, knee_draw, (255, 220, 0), 3)
                        cv2.line(frame, knee_draw, ankle_draw, (255, 220, 0), 3)
                        cv2.circle(frame, shoulder_draw, 7, (0, 255, 0), -1)
                        cv2.circle(frame, hip_draw, 7, (0, 255, 0), -1)
                        cv2.circle(frame, knee_draw, 7, (0, 255, 0), -1)
                        cv2.circle(frame, ankle_draw, 7, (0, 255, 0), -1)

                        if smoothed_points["ear"] is not None:
                            ear_draw = tuple(map(int, smoothed_points["ear"]))
                            cv2.line(frame, ear_draw, shoulder_draw, (255, 80, 80), 3)
                            cv2.circle(frame, ear_draw, 7, (255, 120, 120), -1)

            saved_rows.append(row)

            if show_preview:
                frame_height, frame_width = frame.shape[:2]
                scale = min(MAX_WIDTH / frame_width, MAX_HEIGHT / frame_height, 1.0)
                new_width = int(frame_width * scale)
                new_height = int(frame_height * scale)
                frame_small = cv2.resize(frame, (new_width, new_height))
                cv2.imshow("Analisis", frame_small)

                key = cv2.waitKey(20) & 0xFF
                if key == ord("q"):
                    break

    cap.release()
    if show_preview:
        cv2.destroyAllWindows()

    return saved_rows, saved_changes


def run_analysis(
    video_path,
    reference_csv_path=DEFAULT_REFERENCE_AVERAGES_CSV,
    reference_angles_csv_path=DEFAULT_REFERENCE_ANGLES_CSV,
    reference_changes_csv_path=DEFAULT_REFERENCE_CHANGES_CSV,
    model_path=DEFAULT_MODEL_PATH,
    output_dir=None,
    side=DEFAULT_SIDE,
    start_second=DEFAULT_START_SECOND,
    show_preview=DEFAULT_SHOW_PREVIEW,
):
    video_path = Path(video_path).expanduser().resolve()
    reference_csv_path = Path(reference_csv_path).expanduser().resolve()
    reference_angles_csv_path = Path(reference_angles_csv_path).expanduser().resolve()
    reference_changes_csv_path = Path(reference_changes_csv_path).expanduser().resolve()
    model_path = Path(model_path).expanduser().resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"No se encontro el video: {video_path}")
    if video_path.suffix.lower() not in VIDEO_EXTENSIONS:
        raise ValueError(f"Extension de video no soportada: {video_path.suffix}")
    if not reference_csv_path.exists():
        raise FileNotFoundError(f"No se encontro el CSV de referencia: {reference_csv_path}")
    if not reference_angles_csv_path.exists():
        raise FileNotFoundError(f"No se encontro el CSV de angulos de referencia: {reference_angles_csv_path}")
    if not reference_changes_csv_path.exists():
        raise FileNotFoundError(f"No se encontro el CSV de cambios de referencia: {reference_changes_csv_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"No se encontro el modelo: {model_path}")

    output_paths = resolve_output_paths(video_path, output_dir)

    rows, changes_rows = process_video(
        video_path=video_path,
        model_path=model_path,
        side=side,
        start_second=start_second,
        show_preview=show_preview,
    )
    interpolated_rows = build_interpolated_segments(video_path, rows, changes_rows)
    average_rows = build_segment_averages(interpolated_rows)
    reference_rows = read_rows_from_csv(reference_csv_path)
    reference_angle_rows = read_rows_from_csv(reference_angles_csv_path)
    reference_change_rows = read_rows_from_csv(reference_changes_csv_path)
    reference_pose_index = build_reference_pose_index(reference_angle_rows, reference_change_rows)
    comparison_rows = build_segment_comparisons(interpolated_rows, reference_rows)

    write_rows_to_csv(output_paths["angles"], FIELDNAMES, rows)
    write_rows_to_csv(output_paths["changes"], CHANGE_FIELDNAMES, changes_rows)
    write_rows_to_csv(output_paths["interpolated"], INTERPOLATED_FIELDNAMES, interpolated_rows)
    write_rows_to_csv(output_paths["averages"], AVERAGE_FIELDNAMES, average_rows)
    write_rows_to_csv(output_paths["comparison"], COMPARISON_FIELDNAMES, comparison_rows)
    render_overlay_video(
        video_path=video_path,
        output_video_path=output_paths["overlay_video"],
        rows=rows,
        changes_rows=changes_rows,
        comparison_rows=comparison_rows,
        reference_pose_index=reference_pose_index,
        start_second=start_second,
    )

    return {
        "video_path": video_path,
        "reference_csv_path": reference_csv_path,
        "reference_angles_csv_path": reference_angles_csv_path,
        "reference_changes_csv_path": reference_changes_csv_path,
        "model_path": model_path,
        "output_paths": output_paths,
        "rows": rows,
        "changes_rows": changes_rows,
        "interpolated_rows": interpolated_rows,
        "average_rows": average_rows,
        "comparison_rows": comparison_rows,
    }


def print_analysis_summary(result):
    print(f"Video seleccionado: {result['video_path']}")
    print(f"Referencia cargada: {result['reference_csv_path']}")
    print(f"Referencia de landmarks: {result['reference_angles_csv_path']}")
    print(f"Referencia de cambios: {result['reference_changes_csv_path']}")
    print(f"Modelo cargado: {result['model_path']}")
    print(f"Carpeta de salida: {result['output_paths']['output_dir']}")

    print(f"\nFrames guardados: {len(result['rows'])}")
    print(f"Cambios de direccion detectados: {len(result['changes_rows'])}")
    print(f"Filas interpoladas generadas: {len(result['interpolated_rows'])}")
    print(f"Filas de promedios generadas: {len(result['average_rows'])}")
    print(f"Comparaciones generadas: {len(result['comparison_rows'])}")

    print_comparison_summary(result["comparison_rows"])

    print("\nArchivos generados:")
    print(f"  Angulos: {result['output_paths']['angles']}")
    print(f"  Cambios: {result['output_paths']['changes']}")
    print(f"  Interpolado: {result['output_paths']['interpolated']}")
    print(f"  Promedios: {result['output_paths']['averages']}")
    print(f"  Comparacion: {result['output_paths']['comparison']}")
    print(f"  Video overlay: {result['output_paths']['overlay_video']}")


def main():
    args = parse_args()

    result = run_analysis(
        video_path=choose_video_path(args.video),
        reference_csv_path=args.reference_averages,
        reference_angles_csv_path=args.reference_angles,
        reference_changes_csv_path=args.reference_changes,
        model_path=args.model,
        output_dir=args.output_dir,
        side=args.side,
        start_second=args.start_second,
        show_preview=args.preview,
    )
    print_analysis_summary(result)


if __name__ == "__main__":
    main()
