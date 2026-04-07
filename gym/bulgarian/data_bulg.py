import pandas as pd

ruta = r'C:\Users\WINDOWS\Documents\gym\bulgarian\bulgarian_angles.csv'
data = pd.read_csv(ruta)
print(data.describe)
