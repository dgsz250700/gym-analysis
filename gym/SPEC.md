# Spec

## Objetivo

Construir un pipeline que:

1. procese videos de un ejercicio con MediaPipe Pose
2. detecte landmarks relevantes
3. derive variables biomecanicas de interes
4. segmente el movimiento en fases comparables
5. interpole cada fase a una escala comun `0..100`
6. calcule una referencia promedio desde videos base
7. compare un video input contra esa referencia
8. produzca feedback cuantitativo, cualitativo y visual

## Alcance actual

Ejercicio soportado actualmente:

- Bulgarian Split Squat

Lado analizado:

- `right` por defecto
- `left` soportado por argumento, pero no esta completamente validado con dataset equivalente

Variables de interes actuales:

- `knee_angle_deg`
- `torso_inclination_abs_deg`
- `neck_inclination_abs_deg`

## Entradas

### Referencia

Videos base almacenados en:

- `gym/bulgarian/`

Modelo:

- `gym/pose_landmarker_full.task`

### Input

Un solo video elegido por usuario:

- por CLI en `gym_input.py`
- por selector de archivos en `gym_input_ui.py`

## Pipeline funcional

### A. Construccion de referencia

Script:

- `../gym_try.py`

Responsabilidades:

1. leer videos de referencia
2. detectar landmarks con MediaPipe
3. suavizar puntos y angulos con EMA
4. calcular:
   - rodilla
   - torso
   - cuello
5. detectar cambios de direccion del angulo de rodilla
6. formar segmentos entre eventos consecutivos
7. interpolar cada segmento a `normalized_percent = 0..100`
8. promediar segmentos por `segment_type`

Outputs:

- `bulgarian_angles.csv`
- `bulgarian_angle_changes.csv`
- `bulgarian_interpolated_segments.csv`
- `bulgarian_segment_averages.csv`

### B. Analisis de un video input

Script:

- `bulgarian/gym_input.py`

Responsabilidades:

1. procesar un video individual
2. generar sus CSV de landmarks, cambios, interpolacion y promedios
3. cargar referencia promedio
4. comparar cada segmento contra el promedio de su mismo `segment_type`
5. traducir diferencia porcentual a feedback cualitativo
6. generar overlay visual de input vs promedio

Outputs por video:

- `*_angles.csv`
- `*_angle_changes.csv`
- `*_interpolated_segments.csv`
- `*_segment_averages.csv`
- `*_segment_comparison.csv`
- `*_overlay.mp4`

### C. UI

Script:

- `bulgarian/gym_input_ui.py`

Responsabilidades:

1. permitir seleccionar video
2. correr `run_analysis(...)`
3. mostrar el overlay dentro de la app
4. mostrar resumen textual
5. abrir el CSV de comparacion con un boton

## Segmentacion

Logica actual:

- se observa el cambio de direccion del angulo de rodilla
- `baja_a_sube` y `sube_a_baja` son los eventos canonicos
- un segmento se define entre dos eventos consecutivos
- `segment_type = start_change_direction|end_change_direction`

## Interpolacion

Metodo:

- lineal
- escala fija de `0..100`
- una fila por entero en ese rango

## Comparacion

Base:

- se compara cada segmento del input contra la referencia promedio del mismo `segment_type`

Metricas:

- `mean_signed_pct_diff_*`
- `mean_abs_pct_diff_*`
- `assessment_*`
- `segment_assessment`

Clasificacion actual:

- `0-3%`: `buen ejercicio`
- `4-8%`: `aun se puede mejorar`
- `9-16%`: `es necesario ajustar`
- `17-25%`: `realizar ajustes profundos`
- `>25%`: `riesgo de lesion`

La clasificacion se aplica sobre la diferencia porcentual absoluta promedio.

## Overlay visual

En el video final:

- verde = pose del input
- naranja = pose promedio de referencia
- texto = evaluacion general del segmento

La pose promedio se reconstruye a partir de landmarks de referencia normalizados por escala corporal relativa y luego se reescala sobre el cuerpo del input.

## No objetivos actuales

- Soporte multi ejercicio generalizado
- Configuracion dinamica de variables biomecanicas por ejercicio
- Persistencia en base de datos
- API web
- entrenamiento de modelo propio

## Riesgos tecnicos

- Dependencia fuerte en calidad/visibilidad de landmarks
- Datos de referencia y scripts aun no estan completamente reorganizados
- El repo Git real esta un nivel arriba de `gym/`
- La referencia actual es especifica a un conjunto de videos y un solo ejercicio

## Criterios de aceptacion del estado actual

- se puede generar una referencia promedio a partir del dataset base
- se puede procesar un video nuevo
- se obtiene un CSV de comparacion por segmento
- se obtiene un overlay visual sobre el video
- existe una UI minima funcional para disparar el flujo y abrir el CSV de comparacion

