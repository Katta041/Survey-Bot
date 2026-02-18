import pandas as pd

try:
    df = pd.read_excel('/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx', sheet_name='Data', nrows=5)
    with open('data_columns_full.txt', 'w') as f:
        for col in df.columns:
            f.write(f"{col}\n")
    print("Columns written to data_columns_full.txt")
except Exception as e:
    print(f"Error: {e}")
