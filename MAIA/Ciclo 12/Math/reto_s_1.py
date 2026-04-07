import numpy as np
import math 
import matplotlib.pyplot as plt

v = input("Ingrese un vector de 2 numeros: ").split()

if len(v) != 2:
    print("Error: solo 2 numeros.")
else:
    v_in = np.array([float(x) for x in v])
    print("Vector válido:", v)
angulo = float(input("Ingrese angulo:"))
ang = math.radians(angulo)
matriz = np.array([[math.cos(ang), math.sin(ang)],[-math.sin(ang),math.cos(ang)]])
rotado = v_in @ matriz


plt.plot(v_in)
plt.plot(rotado, color = 'r')
plt.show()