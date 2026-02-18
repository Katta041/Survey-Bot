import pandas as pd
import os
import framework_config as config
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix

def benchmark_results_sarvam():
    results_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'validation_results_sarvam.csv')
    if not os.path.exists(results_path):
        print("Validation results not found.")
        return

    df = pd.read_csv(results_path)
    
    df['gt_bool'] = df['ground_truth_validity'].apply(lambda x: True if str(x).lower() == 'valid' else False)
    df['llm_bool'] = df['llm_is_valid'].astype(bool)

    accuracy = accuracy_score(df['gt_bool'], df['llm_bool'])
    precision = precision_score(df['gt_bool'], df['llm_bool'], zero_division=0)
    recall = recall_score(df['gt_bool'], df['llm_bool'], zero_division=0)
    conf_matrix = confusion_matrix(df['gt_bool'], df['llm_bool'])
    
    tn, fp, fn, tp = conf_matrix.ravel()

    print("\n--- Audio Validation Benchmark (Sarvam AI) ---")
    print(f"Total Samples: {len(df)}")
    print(f"Accuracy: {accuracy:.2f}")
    print(f"Precision: {precision:.2f}")
    print(f"Recall: {recall:.2f}")
    print("\nConfusion Matrix:")
    print(f"True Negatives: {tn}")
    print(f"False Positives: {fp}")
    print(f"False Negatives: {fn}")
    print(f"True Positives: {tp}")

    print("\n--- Detailed Breakdown (First 10 Mismatches) ---")
    mismatch_count = 0
    for index, row in df.iterrows():
        status = "MATCH" if row['gt_bool'] == row['llm_bool'] else "MISMATCH"
        
        if status == "MISMATCH":
            mismatch_count += 1
            if mismatch_count <= 10:
                print(f"Sample {row['sample_id']} | GT: {row['ground_truth_validity']} | LLM: {row['llm_bool']} | {status}")
                print(f"  > LLM Reason: {row['llm_reason']}")
                print(f"  > Transcript: {str(row['transcript'])[:100]}...")
    
    if mismatch_count > 10:
        print(f"... and {mismatch_count - 10} more mismatches.")

if __name__ == "__main__":
    benchmark_results_sarvam()
