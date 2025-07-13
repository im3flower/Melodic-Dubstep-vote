import pandas as pd

file = r'C:\Users\18200\Desktop\md website\md songlist store\songlist.csv'

df = pd.read_csv(file)

df_unique = df.drop_duplicates()

df_unique.to_csv(file, index=False)