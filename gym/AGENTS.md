# AGENTS

Este archivo esta pensado para agentes tipo Codex / Claude / Cursor / copilots similares.

## Proyecto en una frase

Pipeline de analisis de tecnica por video con MediaPipe Pose para Bulgarian Split Squat, con referencia promedio, comparacion porcentual por segmento y overlay visual.

## Regla mas importante

No asumas que la raiz del proyecto coincide con la raiz Git.

Situacion actual:

- raiz Git real: `C:\Users\WINDOWS\Documents`
- proyecto `gym`: `C:\Users\WINDOWS\Documents\gym`
- script de referencia principal: `C:\Users\WINDOWS\Documents\gym_try.py`

Cuando edites o describas el proyecto, deja esto claro.

## Superficie activa de codigo

### Referencia

- `../gym_try.py`

Genera:

- `bulgarian_angles.csv`
- `bulgarian_angle_changes.csv`
- `bulgarian_interpolated_segments.csv`
- `bulgarian_segment_averages.csv`

### Input backend

- `bulgarian/gym_input.py`

Funciones importantes:

- `run_analysis(...)`
- `build_interpolated_segments(...)`
- `build_segment_averages(...)`
- `build_segment_comparisons(...)`
- `render_overlay_video(...)`

### UI

- `bulgarian/gym_input_ui.py`

Uso:

- selecciona un video
- corre `run_analysis(...)`
- reproduce el overlay
- abre el CSV de comparacion

## Invariantes del pipeline

### Segmentacion

- los eventos canonicos son:
  - `baja_a_sube`
  - `sube_a_baja`
- `segment_type` siempre es:
  - `start_change_direction|end_change_direction`

### Variables de interes actuales

- `knee_angle_deg`
- `torso_inclination_abs_deg`
- `neck_inclination_abs_deg`

No cambiar esto sin revisar:

- headers de CSV
- comparacion
- UI resumen
- overlay

### Interpretacion de feedback

La clasificacion se basa en `mean_abs_pct_diff_*`:

- `0-3`: `buen ejercicio`
- `4-8`: `aun se puede mejorar`
- `9-16`: `es necesario ajustar`
- `17-25`: `realizar ajustes profundos`
- `>25`: `riesgo de lesion`

`segment_assessment` toma la peor evaluacion del segmento.

## Si vas a modificar el proyecto

### Haz esto

- manten la compatibilidad de headers en CSV si es posible
- deja claros los defaults de rutas de referencia
- usa salidas nuevas por corrida en la UI si hay archivos reproducidos/abiertos
- documenta cualquier nuevo ejercicio en `README.md`, `SPEC.md` y `HANDOFF.md`

### Evita esto

- no mezcles mas codigo activo nuevo fuera de `gym/` si puedes evitarlo
- no cambies nombres de columnas sin actualizar todo el pipeline
- no asumas que el overlay es solo decorativo; hoy es parte importante del feedback
- no dependas de un video abierto en Excel o reproductores externos para leer resultados

## Archivos / carpetas que son datos, no logica

- `bulgarian/*.mp4`
- `bulgarian/*.csv`
- `bulgarian/ui_runs/`

Tratalos como artefactos o dataset. No deduzcas arquitectura solo por la presencia de outputs generados.

## Prioridades para futuros agentes

1. consolidar la estructura del proyecto
2. parametrizar ejercicio y variables de interes
3. separar datos base, resultados y codigo
4. agregar pruebas automatizadas
5. mejorar la UI para mostrar tabla de comparacion sin depender de Excel

## Antes de cerrar una tarea grande

Confirma al menos:

- que `gym_input.py` siga compilando
- que `gym_input_ui.py` siga compilando
- que los CSV clave mantengan headers coherentes
- que el `overlay.mp4` siga generandose

