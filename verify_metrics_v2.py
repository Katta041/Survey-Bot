import pandas as pd

file_path = '/Users/aierarohit/Desktop/Political Data/_Viralimalai_Overall_V3.xlsx'

try:
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    
    def find_and_print_all(keywords, label):
        print(f"\n--- Searching for {label} ---")
        found = False
        for col in df.columns:
            if all(k.lower() in col.lower() for k in keywords):
                print(f"Found Column: {col[:100]}...")
                print(df[col].value_counts(normalize=True) * 100)
                found = True
        if not found:
            print("No matching column found.")

    # 1. Satisfaction (Look for unique keywords)
    # The previous one was "rate the performance". 
    # Let's look for "satisfied" in other contexts or just "government" generally?
    
    # 2. CM Preference
    # Keywords: "Who", "Chief Minister" (but exclude "performance" or "rate")
    find_and_print_all(['Who', 'Chief Minister'], "CM Preference")

    # 3. Vote 2026
    # Keywords: "Who", "vote", "2026"
    find_and_print_all(['Who', 'vote', '2026'], "Vote 2026")

    # 4. Satisfaction again, check for strict match
    find_and_print_all(['satisf'], "Satisfaction (General)")
    
    # 5. Check Sample Size Again
    print(f"\nTotal Rows: {len(df)}")

except Exception as e:
    print(f"Error: {e}")
