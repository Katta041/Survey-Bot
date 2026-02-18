import pandas as pd

file_path = '/Users/aierarohit/Desktop/Political Data/_Viralimalai_Overall_V3.xlsx'

try:
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    print("All Columns in Sheet1:")
    for col in df.columns:
        print(col)
        
    # Also print some value counts for potential key columns if they exist
    potential_columns = [
        'CM Preference', 'Satisfaction', 'Government Performance', 
        'Change', 'Vote', 'Party', 'Alliance', 'Caste'
    ]
    
    print("\n--- Value Counts for matched columns ---")
    for col in df.columns:
        # Check if any keyword matches part of the column name (case insensitive)
        for keyword in potential_columns:
            if keyword.lower() in col.lower():
                print(f"\nColumn: {col}")
                print(df[col].value_counts().head())

except Exception as e:
    print(f"Error: {e}")
