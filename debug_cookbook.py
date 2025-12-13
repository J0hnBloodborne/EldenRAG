import pandas as pd
import os

filename = 'cookbooks.csv'
if not os.path.exists(filename):
    filename = os.path.join("data/items", filename)

try:
    df = pd.read_csv(filename)
    print(f"--- COLUMNS in {filename} ---")
    print(df.columns.tolist())
    print("\n--- FIRST ROW ---")
    print(df.iloc[0].to_dict())
except Exception as e:
    print(f"Error: {e}")