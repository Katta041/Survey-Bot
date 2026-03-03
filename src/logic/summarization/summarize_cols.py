import pandas as pd

path = "/Users/aierarohit/Desktop/Political Data/Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
df = pd.read_excel(path)

with open('tn_summary.txt', 'w') as f:
    f.write(f"Shape: {df.shape}\n")
    f.write("Columns:\n")
    for c in df.columns:
        f.write(f"- {c}\n")
    
    # Write some sample data for first row
    f.write("\nSample Row 1:\n")
    for c in df.columns:
        f.write(f"{c}: {df.iloc[0][c]}\n")
