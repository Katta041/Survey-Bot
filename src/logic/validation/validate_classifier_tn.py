import pandas as pd
import os
import framework_config as config
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report

def map_human_qc_to_category(qc_status, qc_comment):
    """
    Tries to map the human QC strings into the 1-5 categories for ground truth comparison.
    1) Correctly Done
    2) Not Asking All Questions
    3) Not Doing it Properly
    4) Fake Audio / Empty Audio
    5) Taking Samples from Friends & Relatives
    """
    qc_status = str(qc_status).strip().lower()
    qc_comment = str(qc_comment).strip().lower()
    
    # Priority checks on comments
    if 'fake' in qc_comment or 'empty' in qc_comment or 'no audio' in qc_comment:
        return "4"
    if 'friend' in qc_comment or 'relative' in qc_comment or 'mimicry' in qc_comment:
        return "5"
    if 'properly' in qc_comment or 'mismatch' in qc_comment or 'wrong option' in qc_comment:
        return "3"
    if 'not asking' in qc_comment or 'missing' in qc_comment:
        return "2"
        
    if qc_status == 'done' or qc_status == 'valid':
        # Sometimes 'Done' has comments, check score
        return "1"
        
    # Default assumptions
    if 'not valid' in qc_status:
        return "3"
        
    return "Unknown"

def validate_classifier():
    tn_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_samples')
    metadata_path = os.path.join(tn_dir, "tn_downloaded_metadata.csv")
    results_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_audio_classification_results.csv')

    if not os.path.exists(results_path) or not os.path.exists(metadata_path):
        print("Missing required files to run validation.")
        return

    meta_df = pd.read_csv(metadata_path)
    res_df = pd.read_csv(results_path)

    # Merge to align
    df = pd.merge(res_df, meta_df[['sample_id', 'qc_status', 'qc_comment', 'qc_remark']], on='sample_id', how='inner')
    
    if df.empty:
        print("No intersecting sample IDs found between metadata and results.")
        return

    # Create Ground Truth column
    df['human_category'] = df.apply(lambda row: map_human_qc_to_category(row['qc_status'], row['qc_comment']), axis=1)
    
    # Filter out unknowns we cannot confidently map
    eval_df = df[df['human_category'] != "Unknown"].copy()
    eval_df = eval_df[eval_df['classification_category'].astype(str).isin(['1','2','3','4','5'])]
    
    if eval_df.empty:
        print("Could not parse human categories to evaluate. We will rely on manual spotchecks.")
        # Output raw comparisons
        df.to_csv("tn_validation_mismatches_raw.csv", index=False)
        return
        
    y_true = eval_df['human_category'].astype(str)
    y_pred = eval_df['classification_category'].astype(str)
    
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average='weighted', zero_division=0)
    rec = recall_score(y_true, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)

    print("=== VALIDATION METRICS ===")
    print(f"Total Evaluated Samples: {len(eval_df)}")
    print(f"Accuracy:  {acc:.4f}")
    print(f"Precision: {prec:.4f} (Weighted)")
    print(f"Recall:    {rec:.4f} (Weighted)")
    print(f"F1 Score:  {f1:.4f} (Weighted)")
    print("\nDetailed Report:\n", classification_report(y_true, y_pred, zero_division=0))
    
    # Save mismatched cases for review
    mismatches = eval_df[y_true != y_pred]
    mismatch_file = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_classification_mismatches.csv')
    mismatches.to_csv(mismatch_file, index=False)
    print(f"Mismatch report saved to {mismatch_file}")

if __name__ == "__main__":
    validate_classifier()
