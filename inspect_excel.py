import pandas as pd
import sys

try:
    df = pd.read_excel('/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx', sheet_name='Data', nrows=5)
    print("Columns found in 'Data' sheet:")
    for col in df.columns:
        print(f"- {col}")
except Exception as e:
    print(f"Error reading Excel: {e}")
