import pandas as pd
import os
import framework_config as config
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix

def benchmark_results():
    results_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'validation_results.csv')
    if not os.path.exists(results_path):
        print("Validation results not found. Run validator first.")
        return

    df = pd.read_csv(results_path)
    
    # Map Ground Truth to Boolean
    # 'Valid' -> True, 'Not Valid' -> False
    df['gt_bool'] = df['ground_truth_validity'].apply(lambda x: True if str(x).lower() == 'valid' else False)
    
    # Check for errors in LLM output (defaults to False if error)
    # Ensure llm_is_valid is boolean
    df['llm_bool'] = df['llm_is_valid'].astype(bool)

    # Calculate metrics
    accuracy = accuracy_score(df['gt_bool'], df['llm_bool'])
    precision = precision_score(df['gt_bool'], df['llm_bool'], zero_division=0)
    recall = recall_score(df['gt_bool'], df['llm_bool'], zero_division=0)
    conf_matrix = confusion_matrix(df['gt_bool'], df['llm_bool'])
    
    tn, fp, fn, tp = conf_matrix.ravel()

    print("\n--- Audio Validation Framework Benchmark ---")
    print(f"Total Samples: {len(df)}")
    print(f"Accuracy: {accuracy:.2f}")
    print(f"Precision: {precision:.2f}")
    print(f"Recall: {recall:.2f}")
    print("\nConfusion Matrix:")
    print(f"True Negatives (Correctly identified Invalid): {tn}")
    print(f"False Positives (Incorrectly marked Valid): {fp}")
    print(f"False Negatives (Incorrectly marked Invalid): {fn}")
    print(f"True Positives (Correctly identified Valid): {tp}")

    print("\n--- detailed Breakdown ---")
    for index, row in df.iterrows():
        status = "MATCH" if row['gt_bool'] == row['llm_bool'] else "MISMATCH"
        print(f"Sample {row['sample_id']} | GT: {row['ground_truth_validity']} | LLM: {row['llm_bool']} | {status}")
        if status == "MISMATCH":
            print(f"  > LLM Reason: {row['llm_reason']}")
            print(f"  > QC Remark: {row.get('qc_remark', 'N/A')}")

if __name__ == "__main__":
    benchmark_results()
