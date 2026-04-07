from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from tensorflow import keras
import numpy as np
import librosa
import tempfile
import os


SR               = 22050
N_MELS           = 64
TOP_DB           = 80
SEGMENT_SECONDS  = 1.5   
THRESHOLD        = 0.4    
MODEL_PATH       = r"C:\Users\WINDOWS\Documents\maracuya\modelo_periquitos.keras"

# ──────────────────────────────────────────
# INICIALIZACIÓN
# ──────────────────────────────────────────
app = FastAPI(title="Periquitos API", version="1.0.0")

# CORS: necesario si el cliente es una app web o Flutter Web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # en producción, pon tu dominio específico
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cargar modelo UNA SOLA VEZ al iniciar el servidor
print(f"Cargando modelo desde: {MODEL_PATH}")
model = keras.models.load_model(MODEL_PATH)
print("Modelo cargado correctamente.")


# ──────────────────────────────────────────
# FUNCIONES DE PREPROCESAMIENTO
# ──────────────────────────────────────────
def preprocess_one_segment(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Recibe un array de audio numpy de SEGMENT_SECONDS segundos.
    Devuelve tensor (1, N_MELS, T, 1) listo para la CNN.
    """
    target_len = SEGMENT_SECONDS * sr

    # Asegurar longitud exacta (padding o recorte)
    if len(y) < target_len:
        y = np.pad(y, (0, target_len - len(y)))
    else:
        y = y[:target_len]

    # Mel-spectrogram → escala logarítmica → normalización [0, 1]
    mel     = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=N_MELS)
    log_mel = librosa.power_to_db(mel, ref=np.max, top_db=TOP_DB)
    log_mel = (log_mel + TOP_DB) / TOP_DB

    X = log_mel[np.newaxis, ..., np.newaxis]  # (1, 64, T, 1)
    return X.astype(np.float32)


def segment_and_preprocess(y: np.ndarray, sr: int) -> list:
    """
    Divide el audio completo en segmentos de SEGMENT_SECONDS segundos
    y preprocesa cada uno.
    Retorna lista de tensores listos para predecir.
    """
    segment_len = SEGMENT_SECONDS * sr
    segments    = []

    # Cortar en ventanas sin solapamiento
    for start in range(0, len(y) - segment_len + 1, segment_len):
        seg = y[start : start + segment_len]
        X   = preprocess_one_segment(seg, sr)
        segments.append(X)

    # Si el audio es más corto que un segmento, usar lo que hay (con padding)
    if not segments:
        X = preprocess_one_segment(y, sr)
        segments.append(X)

    return segments


# ──────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────
@app.get("/health")
def health():
    """Verificar que el servidor está vivo."""
    return {"status": "ok", "model_loaded": True}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Recibe un archivo de audio, lo segmenta en ventanas de SEGMENT_SECONDS,
    predice cada segmento y devuelve el promedio.
    """

    # 1. Validar formato
    ALLOWED = (".wav", ".mp3", ".m4a", ".ogg", ".flac")
    if not file.filename.lower().endswith(ALLOWED):
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Sube: {', '.join(ALLOWED)}"
        )

    # 2. Guardar archivo temporalmente y cargar con librosa
    tmp_path = None
    try:
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            contents = await file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        y, sr = librosa.load(tmp_path, sr=SR, mono=True)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo leer el audio: {repr(e)}"
        )
    finally:
        # Siempre borrar el archivo temporal
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 3. Segmentar y preprocesar
    segments = segment_and_preprocess(y, SR)

    # 4. Predecir cada segmento
    probs = []
    for X in segments:
        prob = float(model.predict(X, verbose=0).ravel()[0])
        probs.append(round(prob, 4))

    # 5. Promediar y decidir etiqueta final
    prob_final = float(np.mean(probs))
    label      = "feliz" if prob_final >= THRESHOLD else "estres"

    # 6. Respuesta completa
    return {
        "label"               : label,
        "duracion_segundos"   : round(len(y) / SR, 2),
        "segmentos_analizados": len(probs),
    }


