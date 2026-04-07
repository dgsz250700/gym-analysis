import csv
import math
from pathlib import Path

import cv2
import mediapipe as mp

video_dir = Path(r"C:/Users/WINDOWS/Documents/gym/bulgarian")
model_filename = "pose_landmarker_full.task"
output_csv_path = video_dir / "bulgarian_angles.csv"
output_changes_csv_path = video_dir / "bulgarian_angle_changes.csv"
video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v"}

inicio_segundo = 0
mostrar_preview = False
reprocesar_todos = False

max_ancho = 1000
max_alto = 700
lado = "right"  # "right" o "left"
alpha_puntos = 0.25
alpha_angulo = 0.2
min_visibilidad = 0.6
umbral_cambio_angulo = 0.5

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


def ema(actual, previo, alpha):
    if previo is None:
        return actual
    return alpha * actual + (1 - alpha) * previo


def ema_punto(actual, previo, alpha):
    if previo is None:
        return actual
    return (
        ema(actual[0], previo[0], alpha),
        ema(actual[1], previo[1], alpha),
    )


def calcular_angulo(a, b, c):
    ab = (a[0] - b[0], a[1] - b[1])
    cb = (c[0] - b[0], c[1] - b[1])

    mag_ab = math.hypot(ab[0], ab[1])
    mag_cb = math.hypot(cb[0], cb[1])
    if mag_ab == 0 or mag_cb == 0:
        return None

    cos_theta = (ab[0] * cb[0] + ab[1] * cb[1]) / (mag_ab * mag_cb)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return math.degrees(math.acos(cos_theta))


def calcular_inclinacion_vertical(punto_superior, punto_inferior):
    dx = punto_superior[0] - punto_inferior[0]
    dy = punto_superior[1] - punto_inferior[1]
    if dx == 0 and dy == 0:
        return None, None

    angulo_firmado = math.degrees(math.atan2(dx, -dy))
    return angulo_firmado, abs(angulo_firmado)


def obtener_indices(lado_cuerpo):
    if lado_cuerpo == "left":
        return 7, 11, 23, 25, 27
    return 8, 12, 24, 26, 28


def crear_row_base(video_path, frame_idx, timestamp_ms):
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


def obtener_videos(folder_path):
    return sorted(
        [
            path
            for path in folder_path.iterdir()
            if path.is_file() and path.suffix.lower() in video_extensions
        ]
    )


def resolver_model_path(folder_path, model_name):
    candidates = [
        folder_path / model_name,
        folder_path.parent / model_name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def preparar_csv(csv_path, fieldnames):
    if not csv_path.exists():
        return set(), True

    with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        existing_header = next(reader, None)

    if existing_header == fieldnames:
        videos_ya_procesados = set()
        with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if row.get("video_name"):
                    videos_ya_procesados.add(row["video_name"])
        return videos_ya_procesados, False

    backup_path = csv_path.with_name(f"{csv_path.stem}_legacy_backup{csv_path.suffix}")
    contador = 1
    while backup_path.exists():
        backup_path = csv_path.with_name(f"{csv_path.stem}_legacy_backup_{contador}{csv_path.suffix}")
        contador += 1

    csv_path.replace(backup_path)
    print(f"CSV anterior movido a: {backup_path}")
    return set(), True


def append_rows_to_csv(csv_path, rows, write_header, fieldnames):
    if not rows and not write_header:
        return

    mode = "a"
    if write_header:
        mode = "w"

    with open(csv_path, mode, newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def procesar_video(video_path):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"No se pudo abrir: {video_path}")
        return [], False

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30

    cap.set(cv2.CAP_PROP_POS_MSEC, inicio_segundo * 1000)

    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model_path)),
        running_mode=VisionRunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    ear_idx, shoulder_idx, hip_idx, knee_idx, ankle_idx = obtener_indices(lado)
    smoothed_points = {"ear": None, "shoulder": None, "hip": None, "knee": None, "ankle": None}
    angulo_rodilla_suave = None
    angulo_torso_firmado_suave = None
    angulo_cuello_firmado_suave = None
    resultados_guardados = []
    cambios_guardados = []
    detener_todo = False
    ultimo_angulo_rodilla = None
    ultimo_frame_angulo = None
    ultimo_timestamp_angulo = None
    ultima_direccion = None
    ultimo_delta = None

    with PoseLandmarker.create_from_options(options) as landmarker:
        if mostrar_preview:
            cv2.namedWindow("Analisis", cv2.WINDOW_NORMAL)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            timestamp_ms = int((frame_idx / fps) * 1000)
            row = crear_row_base(video_path, frame_idx, timestamp_ms)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                h, w = frame.shape[:2]

                ear_lm = landmarks[ear_idx]
                shoulder_lm = landmarks[shoulder_idx]
                hip_lm = landmarks[hip_idx]
                knee_lm = landmarks[knee_idx]
                ankle_lm = landmarks[ankle_idx]

                vis_ok = (
                    shoulder_lm.visibility >= min_visibilidad
                    and hip_lm.visibility >= min_visibilidad
                    and knee_lm.visibility >= min_visibilidad
                    and ankle_lm.visibility >= min_visibilidad
                )

                if vis_ok:
                    shoulder = (shoulder_lm.x * w, shoulder_lm.y * h)
                    hip = (hip_lm.x * w, hip_lm.y * h)
                    knee = (knee_lm.x * w, knee_lm.y * h)
                    ankle = (ankle_lm.x * w, ankle_lm.y * h)

                    smoothed_points["shoulder"] = ema_punto(shoulder, smoothed_points["shoulder"], alpha_puntos)
                    smoothed_points["hip"] = ema_punto(hip, smoothed_points["hip"], alpha_puntos)
                    smoothed_points["knee"] = ema_punto(knee, smoothed_points["knee"], alpha_puntos)
                    smoothed_points["ankle"] = ema_punto(ankle, smoothed_points["ankle"], alpha_puntos)

                    angulo_rodilla_actual = calcular_angulo(
                        smoothed_points["hip"],
                        smoothed_points["knee"],
                        smoothed_points["ankle"],
                    )
                    if angulo_rodilla_actual is not None:
                        angulo_rodilla_suave = ema(angulo_rodilla_actual, angulo_rodilla_suave, alpha_angulo)

                    angulo_torso_firmado_actual, _ = calcular_inclinacion_vertical(
                        smoothed_points["shoulder"],
                        smoothed_points["hip"],
                    )
                    if angulo_torso_firmado_actual is not None:
                        angulo_torso_firmado_suave = ema(
                            angulo_torso_firmado_actual,
                            angulo_torso_firmado_suave,
                            alpha_angulo,
                        )

                    angulo_cuello_firmado_actual = None
                    if ear_lm.visibility >= min_visibilidad:
                        ear = (ear_lm.x * w, ear_lm.y * h)
                        smoothed_points["ear"] = ema_punto(ear, smoothed_points["ear"], alpha_puntos)
                        angulo_cuello_firmado_actual, _ = calcular_inclinacion_vertical(
                            smoothed_points["ear"],
                            smoothed_points["shoulder"],
                        )

                    if angulo_cuello_firmado_actual is not None:
                        angulo_cuello_firmado_suave = ema(
                            angulo_cuello_firmado_actual,
                            angulo_cuello_firmado_suave,
                            alpha_angulo,
                        )

                    if mostrar_preview:
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
                            "knee_angle_deg": round(angulo_rodilla_suave, 2) if angulo_rodilla_suave is not None else None,
                            "torso_inclination_signed_deg": round(angulo_torso_firmado_suave, 2) if angulo_torso_firmado_suave is not None else None,
                            "torso_inclination_abs_deg": round(abs(angulo_torso_firmado_suave), 2) if angulo_torso_firmado_suave is not None else None,
                            "neck_inclination_signed_deg": round(angulo_cuello_firmado_suave, 2) if angulo_cuello_firmado_suave is not None else None,
                            "neck_inclination_abs_deg": round(abs(angulo_cuello_firmado_suave), 2) if angulo_cuello_firmado_suave is not None else None,
                        }
                    )

                    if angulo_rodilla_suave is not None:
                        if ultimo_angulo_rodilla is not None:
                            delta_actual = angulo_rodilla_suave - ultimo_angulo_rodilla

                            if abs(delta_actual) >= umbral_cambio_angulo:
                                direccion_actual = "sube" if delta_actual > 0 else "baja"

                                if (
                                    ultima_direccion is not None
                                    and direccion_actual != ultima_direccion
                                    and ultimo_frame_angulo is not None
                                ):
                                    cambios_guardados.append(
                                        {
                                            "video_name": video_path.name,
                                            "frame_cambio": ultimo_frame_angulo,
                                            "tiempo_ms": ultimo_timestamp_angulo,
                                            "knee_angle_deg": round(ultimo_angulo_rodilla, 2),
                                            "delta_previo_deg": round(ultimo_delta, 2) if ultimo_delta is not None else None,
                                            "delta_actual_deg": round(delta_actual, 2),
                                            "cambio_direccion": f"{ultima_direccion}_a_{direccion_actual}",
                                        }
                                    )

                                ultima_direccion = direccion_actual
                                ultimo_delta = delta_actual

                        ultimo_angulo_rodilla = angulo_rodilla_suave
                        ultimo_frame_angulo = frame_idx
                        ultimo_timestamp_angulo = timestamp_ms

            resultados_guardados.append(row)

            if mostrar_preview:
                h, w = frame.shape[:2]
                escala = min(max_ancho / w, max_alto / h, 1.0)
                nuevo_ancho = int(w * escala)
                nuevo_alto = int(h * escala)
                frame_small = cv2.resize(frame, (nuevo_ancho, nuevo_alto))
                cv2.imshow("Analisis", frame_small)

                tecla = cv2.waitKey(20) & 0xFF
                if tecla == ord("q"):
                    detener_todo = True
                    break

    cap.release()
    if mostrar_preview:
        cv2.destroyAllWindows()

    return resultados_guardados, cambios_guardados, detener_todo


model_path = resolver_model_path(video_dir, model_filename)

if not model_path.exists():
    raise FileNotFoundError(f"No se encontro el modelo: {model_path}")

videos = obtener_videos(video_dir)
if not videos:
    raise FileNotFoundError(f"No se encontraron videos en: {video_dir}")

videos_ya_procesados, escribir_header = preparar_csv(output_csv_path, FIELDNAMES)
videos_con_cambios, escribir_header_cambios = preparar_csv(output_changes_csv_path, CHANGE_FIELDNAMES)

if reprocesar_todos:
    videos_pendientes = videos
else:
    videos_pendientes = [
        video
        for video in videos
        if video.name not in videos_ya_procesados or video.name not in videos_con_cambios
    ]

print(f"Videos encontrados: {len(videos)}")
print(f"Videos pendientes: {len(videos_pendientes)}")

frames_totales = 0

for video_path in videos_pendientes:
    print(f"Procesando: {video_path.name}")
    rows, cambios_rows, detener_todo = procesar_video(video_path)

    if reprocesar_todos or video_path.name not in videos_ya_procesados:
        append_rows_to_csv(output_csv_path, rows, escribir_header, FIELDNAMES)
        escribir_header = False
        frames_totales += len(rows)
        print(f"Frames guardados para {video_path.name}: {len(rows)}")

    if reprocesar_todos or video_path.name not in videos_con_cambios:
        append_rows_to_csv(output_changes_csv_path, cambios_rows, escribir_header_cambios, CHANGE_FIELDNAMES)
        escribir_header_cambios = False
        print(f"Cambios de direccion guardados para {video_path.name}: {len(cambios_rows)}")

    if detener_todo:
        print("Procesamiento detenido por el usuario.")
        break

print(f"Frames agregados al CSV en esta corrida: {frames_totales}")
print(f"CSV final: {output_csv_path}")
print(f"CSV de cambios: {output_changes_csv_path}")
