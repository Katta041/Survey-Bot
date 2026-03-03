import pandas as pd
import os
import framework_config as config

csv_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_audio_classification_results.csv')
excel_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_audio_classification_results.xlsx')

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    df.to_excel(excel_path, index=False)
    print(f"Successfully created Excel file at: {excel_path}")
else:
    print(f"Could not find CSV at {csv_path}")
