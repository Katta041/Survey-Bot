import pandas as pd

file_path = '/Users/aierarohit/Desktop/Political Data/_Viralimalai_Overall_V3.xlsx'

try:
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    total_respondents = len(df)
    print(f"Total Respondents: {total_respondents}")

    def find_and_print(keywords, label):
        found_col = None
        for col in df.columns:
            if all(k.lower() in col.lower() for k in keywords):
                found_col = col
                break
        
        if found_col:
            print(f"\n--- {label} (Column: {found_col[:50]}...) ---")
            counts = df[found_col].value_counts(normalize=True) * 100
            print(counts)
        else:
            print(f"\nCould not find column for {label}")

    # 1. Government Satisfaction
    find_and_print(['satisf', 'DMK'], "Government Satisfaction")

    # 2. Change in Government
    find_and_print(['change', 'government'], "Want Change?")

    # 3. CM Preference
    find_and_print(['Chief Minister'], "CM Preference")

    # 4. 2026 Vote Preference
    find_and_print(['2026', 'vote'], "2026 Vote Preference")
    
    # 5. Vijay's Impact
    find_and_print(['Vijay', 'impact'], "Vijay's Impact")

except Exception as e:
    print(f"Error: {e}")
