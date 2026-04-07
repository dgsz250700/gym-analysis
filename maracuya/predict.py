import librosa
import numpy as np
from tensorflow import keras

ruta_modelo = r'C:\Users\WINDOWS\Documents\maracuya\modelo_periquitos.keras'
# cargar modelo
model = keras.models.load_model(ruta_modelo)

SR = 22050

def preprocess_audio(file_path):
    y, _ = librosa.load(file_path, sr=SR)

    # tomar solo los primeros 3 segundos
    segment = y[:SR*3]

    # si es más corto, hacer padding
    if len(segment) < SR*3:
        padding = SR*3 - len(segment)
        segment = np.pad(segment, (0, padding))

    mel = librosa.feature.melspectrogram(y=segment, sr=SR, n_mels=64)
    log_mel = librosa.power_to_db(mel, ref=np.max, top_db=80)
    log_mel = (log_mel + 80) / 80

    log_mel = log_mel[np.newaxis, ..., np.newaxis]  # (1,64,130,1)
    return log_mel

path = r'C:\Users\WINDOWS\Documents\maracuya\Prueba_e1.wav'
# usar el modelo
X_new = preprocess_audio(path)

prob = model.predict(X_new)[0][0]

umbral = 0.4  # el que decidiste usar
pred = int(prob > umbral)


if pred == 0:
    print("Predicción: Estrés")
else:
    print("Predicción: Feliz")

print("Probabilidad feliz:", prob)