# Handoff

## Resumen rapido

Proyecto de analisis biomecanico por video usando MediaPipe Pose.

Hoy el caso operativo es:

- ejercicio: Bulgarian Split Squat
- referencia: dataset en `gym/bulgarian/`
- pipeline de referencia: `../gym_try.py`
- pipeline de input: `gym/bulgarian/gym_input.py`
- UI: `gym/bulgarian/gym_input_ui.py`

## Estado actual

### Lo que ya funciona

- generacion de CSV de landmarks por frame
- deteccion de cambios de direccion en rodilla
- segmentacion del movimiento
- interpolacion lineal `0..100`
- promedio por tipo de segmento
- comparacion porcentual contra referencia
- etiquetado cualitativo del resultado
- overlay de input vs promedio
- UI minima con selector de video y boton para abrir el CSV

### Archivos clave

- `../gym_try.py`
  - genera la referencia desde videos base
- `gym/bulgarian/gym_input.py`
  - backend del flujo de input
  - expone `run_analysis(...)`
- `gym/bulgarian/gym_input_ui.py`
  - UI en `tkinter`
- `gym/pose_landmarker_full.task`
  - modelo principal

## Outputs canonicos

### Referencia

- `bulgarian_angles.csv`
- `bulgarian_angle_changes.csv`
- `bulgarian_interpolated_segments.csv`
- `bulgarian_segment_averages.csv`

### Por input

- `*_angles.csv`
- `*_angle_changes.csv`
- `*_interpolated_segments.csv`
- `*_segment_averages.csv`
- `*_segment_comparison.csv`
- `*_overlay.mp4`

La UI guarda cada corrida en una subcarpeta unica tipo:

- `bulgarian/ui_runs/<video>_ui_<timestamp>/`

Esto se hizo para evitar bloqueos de archivos entre corridas.

## Decisiones importantes ya tomadas

1. Los eventos de segmento se nombran con los labels originales:
   - `baja_a_sube`
   - `sube_a_baja`
2. La comparacion se hace por `segment_type`, no por video completo.
3. El feedback cualitativo usa porcentaje absoluto promedio.
4. La evaluacion general del segmento toma la peor variable.
5. La referencia visual del overlay se reconstruye usando landmarks normalizados, no solo angulos.

## Riesgos / deuda tecnica

### 1. Estructura del proyecto

El repo Git real esta en `C:\Users\WINDOWS\Documents`, no en `gym/`.

Eso significa que:

- `gym/` no es la raiz Git
- `gym_try.py` vive fuera de `gym/`
- para otra persona o agente esto no es obvio

Ideal futuro:

- mover el flujo completo a una raiz de proyecto consistente

### 2. Hardcoding del ejercicio

Muchos defaults siguen acoplados a Bulgarian:

- nombres de CSV
- carpeta de referencia
- variables de interes
- criterio de comparacion

### 3. Datos generados mezclados con datos fuente

`bulgarian/` contiene:

- videos base
- videos de prueba
- CSV derivados
- overlays
- scripts

Conviene separar al menos:

- `data/raw`
- `data/reference`
- `data/runs`
- `src`

### 4. UI minima

La UI es funcional pero simple:

- no tiene barra de progreso real
- no permite configurar ejercicio
- no embebe una tabla del CSV
- solo abre el archivo en Excel

## Que revisar primero si algo falla

### Si falla la UI despues de varias corridas

Revisar:

- que se sigan creando carpetas unicas en `ui_runs/`
- que no haya callbacks de reproduccion colgados
- que el `overlay.mp4` exista en la salida

### Si el overlay sale mal alineado

Revisar:

- `build_reference_pose_index(...)`
- `normalize_pose_points(...)`
- `denormalize_pose_points(...)`
- `render_overlay_video(...)`

### Si la comparacion sale vacia

Revisar:

- `segment_type` del input
- si existe el mismo `segment_type` en `bulgarian_segment_averages.csv`
- cantidad de cambios detectados en `*_angle_changes.csv`

## Siguientes pasos recomendados

1. mover `gym_try.py` dentro de `gym/`
2. extraer constantes/config a un modulo comun
3. volver configurables las variables de interes por ejercicio
4. separar datos fuente de outputs generados
5. decidir si la UI seguira en `tkinter` o se migrara a web/desktop mas robusto
6. agregar tests para:
   - segmentacion
   - interpolacion
   - clasificacion de feedback
   - render de overlay

## Comandos utiles

### CLI input

```powershell
python C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input.py
```

### UI

```powershell
python C:\Users\WINDOWS\Documents\gym\bulgarian\gym_input_ui.py
```

### Rebuild referencia

```powershell
python C:\Users\WINDOWS\Documents\gym_try.py
```

