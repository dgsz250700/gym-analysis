# PROYECTO DISCAPACIDAD CAPILAR

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

carpeta = r'C:\Users\WINDOWS\Documents\calva'
all_pixels = []  # renamed for clarity

for nombre in os.listdir(carpeta):
    ruta_completa = os.path.join(carpeta, nombre)
    img = cv2.imread(ruta_completa)
    if img is None:
        continue
    img = cv2.resize(img, (512, 512))
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    pixel_values = img_gray.reshape((-1, 1))       # shape: (262144, 1)
    pixel_values = np.float32(pixel_values)
    all_pixels.append(pixel_values)

# Stack all images into a single array for k-means
all_pixels = np.vstack(all_pixels)                 # shape: (N*262144, 1)
print("Shape del dataset:", all_pixels.shape)

k = 2
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

# ✅ Run k-means on ALL pixels, not just the last image
_, labels, centers = cv2.kmeans(
    all_pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS
)

print("Centros de los clusters:", centers)
print("Labels shape:", labels.shape)