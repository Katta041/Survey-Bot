import pandas as pd

file_path = '/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx'

try:
    xl = pd.ExcelFile(file_path)
    df = xl.parse('Data')
    
    # Inspect QC Columns
    qc_cols = ['QC Username', 'QC Comment', 'QC Remark', 'Valid or Not']
    print("\n--- QC Columns Inspection ---")
    for col in qc_cols:
        if col in df.columns:
            print(f"\nColumn: {col}")
            print(df[col].unique()[:10]) # Show first 10 unique values
            print("Null count:", df[col].isnull().sum())

    # Inspect Question Columns (Q1 - Q5)
    q_cols = [c for c in df.columns if c.startswith('Q')]
    print("\n--- Question Columns Inspection ---")
    for col in q_cols[:5]: # Check first 5 questions
        print(f"\nColumn: {col}")
        print(df[col].head(5))

except Exception as e:
    print(f"Error: {e}")
