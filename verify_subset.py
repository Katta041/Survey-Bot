import pandas as pd

file_path = '/Users/aierarohit/Desktop/Political Data/_Viralimalai_Overall_V3.xlsx'

try:
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    
    # Identify columns
    col_performance = [c for c in df.columns if 'performance' in c.lower() and 'Stalin' in c][0]
    col_cm = [c for c in df.columns if 'support' in c.lower() and 'Chief Minister' in c][0]
    
    print(f"Performance Column: {col_performance[:50]}...")
    print(f"CM Column: {col_cm[:50]}...")

    # Filter for 'Needs Improvement'
    needs_improvement = df[df[col_performance].str.contains('Needs improvement', na=False)]
    print(f"\n--- CM Preference among 'Needs Improvement' group (N={len(needs_improvement)}) ---")
    print(needs_improvement[col_cm].value_counts(normalize=True) * 100)

    # Filter for 'Unsatisfied'
    unsatisfied = df[df[col_performance].str.contains('Unsatisfactory', na=False)]
    print(f"\n--- CM Preference among 'Unsatisfied' group (N={len(unsatisfied)}) ---")
    print(unsatisfied[col_cm].value_counts(normalize=True) * 100)

except Exception as e:
    print(f"Error: {e}")
