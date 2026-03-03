import pandas as pd
import os
import framework_config as config
from validate_classifier_tn import map_human_qc_to_category

def show_category_breakdown():
    tn_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_samples')
    metadata_path = os.path.join(tn_dir, "tn_downloaded_metadata.csv")
    results_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_audio_classification_results.csv')

    meta_df = pd.read_csv(metadata_path)
    res_df = pd.read_csv(results_path)

    df = pd.merge(res_df, meta_df[['sample_id', 'qc_status', 'qc_comment', 'qc_remark']], on='sample_id', how='inner')
    df['Actual (Human)'] = df.apply(lambda row: map_human_qc_to_category(row['qc_status'], row['qc_comment']), axis=1)
    
    # Filter out unknowns we cannot confidently map
    eval_df = df[df['Actual (Human)'] != "Unknown"].copy()
    eval_df = eval_df[eval_df['classification_category'].astype(str).isin(['1','2','3','4','5'])]
    
    eval_df['Predicted (LLM)'] = eval_df['classification_category'].astype(str)
    
    # Crosstab
    crosstab = pd.crosstab(eval_df['Actual (Human)'], eval_df['Predicted (LLM)'], margins=True, margins_name="Total")
    
    print("\n=== Actual vs Predicted (Category Level) ===\n")
    print(crosstab.to_string())
    
if __name__ == "__main__":
    show_category_breakdown()
