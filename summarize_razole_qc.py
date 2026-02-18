import pandas as pd

file_path = '/Users/aierarohit/Desktop/Political Data/Razole_Overall Data_V2.xlsx'

try:
    xl = pd.ExcelFile(file_path)
    df = xl.parse('Data')
    
    print(f"Total Records: {len(df)}")
    
    if 'Valid or Not' in df.columns:
        print("\n--- Validity Status ---")
        print(df['Valid or Not'].value_counts())
        print(f"Validity Percentage:\n{df['Valid or Not'].value_counts(normalize=True)*100}")

    if 'QC Remark' in df.columns:
        print("\n--- Top QC Remarks (Issues Found) ---")
        # Filter out '0' or empty remarks if they signify 'No Issue'
        issues = df[df['QC Remark'] != 0]['QC Remark']
        print(issues.value_counts().head(10))

    if 'QC Comment' in df.columns:
        print("\n--- Top QC Comments ---")
        comments = df[df['QC Comment'] != 0]['QC Comment']
        print(comments.value_counts().head(10))

except Exception as e:
    print(f"Error: {e}")
