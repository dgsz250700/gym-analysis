import librosa
import numpy as np
import os
import sklearn
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, mean_squared_error, confusion_matrix, classification_report
from sklearn import preprocessing
from sklearn.preprocessing import LabelEncoder
import tensorflow as tf
from sklearn.model_selection import train_test_split, KFold, GridSearchCV
from tensorflow import keras
from sklearn.utils import shuffle

def segment_audio(file_path, segment_length=3, overlap=0.5, sr=22050):
    y, sr = librosa.load(file_path, sr=sr)

    segment_samples = int(segment_length * sr)
    step = int(segment_samples * (1 - overlap))

    segments = []

    for start in range(0, len(y) - segment_samples + 1, step):
        end = start + segment_samples
        segments.append(y[start:end])

    return segments


carpeta = r'C:\Users\WINDOWS\Documents\Maracuya\Archivos_audio\Estres'
carpeta2 = r'C:\Users\WINDOWS\Documents\Maracuya\Archivos_audio\Feliz'
SR = 22050

X_estres = []  # lista para acumular features
y_estres = []
X_feliz = []
y_feliz = []

data = train_test_split(data,test_size=0.2,random_state=77)


for nombre in os.listdir(carpeta):
    if nombre.lower().endswith('.wav'):
        ruta_completa = os.path.join(carpeta, nombre)
        segmentos = segment_audio(ruta_completa, segment_length=3, overlap=0.5, sr=SR)

        for segment in segmentos:
            mel = librosa.feature.melspectrogram(y=segment, sr=SR, n_mels=64)
            log_mel = librosa.power_to_db(mel)
            log_mel = (log_mel + 80) / 80 
            rms = librosa.feature.rms(y=segment).mean()
            if rms < 0.01:
                continue   # descarta silencios
            X_estres.append(log_mel)
            y_estres.append(0)
                        
for nombre in os.listdir(carpeta2):
    if nombre.lower().endswith('.wav'):
        ruta_completa = os.path.join(carpeta2, nombre)
        segmentos = segment_audio(ruta_completa, segment_length=3, overlap=0.5, sr=SR)

        for segment in segmentos:
            mel = librosa.feature.melspectrogram(y=segment, sr=SR, n_mels=64)
            log_mel = librosa.power_to_db(mel)
            log_mel = (log_mel + 80) / 80 
            rms = librosa.feature.rms(y=segment).mean()
            if rms < 0.01:
                continue   # descarta silencios
            X_feliz.append(log_mel) 
            y_feliz.append(1)   

X_estres = np.array(X_estres)   
y_estres = np.array(y_estres)
X_feliz = np.array(X_feliz)    
y_feliz = np.array(y_feliz)                # (samples, 64, frames)
X_feliz = X_feliz[..., np.newaxis]             # (samples, 64, frames, 1)  ← para CNN 2D
X_estres = X_estres[..., np.newaxis]   



X = np.concatenate((X_estres, X_feliz), axis=0)
y = np.concatenate((y_estres, y_feliz), axis=0)
X, y = shuffle(X, y, random_state=77)