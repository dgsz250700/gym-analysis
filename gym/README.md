# Gym Motion Analysis

Proyecto para analizar tecnica de ejercicios a partir de video usando MediaPipe Pose.

Estado actual:

- El flujo principal hoy esta enfocado en Bulgarian Split Squat.
- Se genera una referencia promedio desde varios videos base.
- Luego se procesa un video input, se segmenta por fases del movimiento, se compara contra la referencia y se produce:
  - video con overlays
  - CSV de comparacion
  - CSV intermedios para depuracion y analisis
- Existe una UI basica de escritorio para correr el flujo sin usar linea de comandos.

## Donde esta cada cosa

La estructura actual no esta totalmente consolidada en una sola carpeta:

- `../gym_try.py`
  - Script de referencia.
  - Procesa los videos base y genera los CSV promedio del ejercicio.
- `bulgarian/gym_input.py`
  - Backend para procesar un video nuevo.
  - Segmenta, interpola, compara y renderiza el video overlay.
- `bulgarian/gym_input_ui.py`
  - Interfaz basica en `tkinter`.
- `pose_landmarker_full.task`
  - Modelo local de MediaPipe usado por el pipeline.
  - No se versiona en Git.
- `bulgarian/`
  - Dataset local del ejercicio, pruebas, outputs y scripts asociados al flujo actual.
  - Los 4 CSV de referencia canonicos si se versionan en Git.

## Flujo actual

### 1. Construir referencia

Se corre `../gym_try.py` sobre videos de referencia en `bulgarian/`.

Outputs principales:

- `bulgarian/bulgarian_angles.csv`
- `bulgarian/bulgarian_angle_changes.csv`
- `bulgarian/bulgarian_interpolated_segments.csv`
- `bulgarian/bulgarian_segment_averages.csv`

### 2. Procesar un video nuevo

Se corre `bulgarian/gym_input.py` o la UI `bulgarian/gym_input_ui.py`.

Para cada video input se generan:

- `*_angles.csv`
- `*_angle_changes.csv`
- `*_interpolated_segments.csv`
- `*_segment_averages.csv`
- `*_segment_comparison.csv`
- `*_overlay.mp4`

Estos outputs se consideran artefactos locales y no deben versionarse, excepto los 4 CSV canonicos de referencia:

- `bulgarian_angle_changes.csv`
- `bulgarian_angles.csv`
- `bulgarian_interpolated_segments.csv`
- `bulgarian_segment_averages.csv`

## Variables de interes actuales

Por ahora el sistema compara estas 3 variables:

- `knee_angle_deg`
- `torso_inclination_abs_deg`
- `neck_inclination_abs_deg`

Todavia no son configurables por ejercicio; hoy estan hardcodeadas para el caso de Bulgarian Split Squat.

## Como correrlo

### Opcion 1. Script por terminal

```powershell
python C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py
```

O pasando un video especifico:

```powershell
python C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py C:\ruta\video.mp4
```

### Opcion 2. UI basica

```powershell
python C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input_ui.py
```

La UI:

- deja elegir un video
- corre el procesamiento
- reproduce el overlay dentro de la ventana
- muestra el resumen de comparacion
- abre el CSV de comparacion con un clic

## Interpretacion de resultados

El sistema calcula diferencia porcentual contra la referencia promedio y la traduce a etiquetas:

- `0-3%`: `buen ejercicio`
- `4-8%`: `aun se puede mejorar`
- `9-16%`: `es necesario ajustar`
- `17-25%`: `realizar ajustes profundos`
- `>25%`: `riesgo de lesion`

La evaluacion general del segmento toma la peor evaluacion entre las variables de interes.

## Limitaciones conocidas

- La referencia y el input todavia estan acoplados a un solo ejercicio.
- La arquitectura actual mezcla codigo en `gym/` con un script clave afuera en `../gym_try.py`.
- El overlay de referencia se reconstruye a partir de landmarks promedio normalizados; es una guia visual, no una "pose real" exacta.
- Hay muchos archivos generados dentro de `bulgarian/`; conviene limpiar outputs viejos antes de versionar.

## Politica de versionado

Este repo debe contener:

- codigo fuente `.py`
- documentacion `.md`
- la configuracion minima de Git como `.gitignore`
- los 4 CSV canonicos de referencia en `gym/bulgarian/`

No deben versionarse:

- videos `.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v`
- CSV generados o usados como artefactos de trabajo, salvo los 4 canonicos de referencia
- modelos `.task`
- imagenes de referencia
- carpetas de salidas como `bulgarian/ui_runs/`

## Archivos recomendados para leer primero

- `README.md`
- `SPEC.md`
- `HANDOFF.md`
- `AGENTS.md`
