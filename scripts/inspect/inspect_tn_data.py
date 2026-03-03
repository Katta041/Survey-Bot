import pandas as pd

excel_path = "/Users/aierarohit/Desktop/Political Data/Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
df = pd.read_excel(excel_path)
print("Columns:", df.columns.tolist())
print("\nFirst row sample:")
print(df.iloc[0].to_dict())

print(f"\nTotal rows: {len(df)}")
