import os
import librosa 

#y es serie de tiempo
#sr es tasa de muestreo de y 
archivo = 'pollo1.m4a'
y,sr = librosa.load(archivo)
librosa.stft()
librosa.amplitude_to_db()