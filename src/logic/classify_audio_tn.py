import pandas as pd
import json
import os
import sys
from openai import OpenAI
import framework_config as config

# Use GPT-4o as it is highly capable in multilingual (Tamil) reasoning and instruction following.
# If Claude or Gemini keys are available, the client can be swapped, but OpenAI gpt-4o is current SOTA.
client = OpenAI(api_key=config.OPENAI_API_KEY)

MODEL_NAME = "gpt-4o"

def classify_tn_audio(sample_limit=None):
    tn_dir = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_samples')
    metadata_path = os.path.join(tn_dir, "tn_transcribed_metadata_sarvam.csv")
    
    if not os.path.exists(metadata_path):
        # Fallback to downloaded metadata if transcription merged there
        metadata_path = os.path.join(tn_dir, "tn_downloaded_metadata.csv")

    print(f"Loading data from {metadata_path}")
    df = pd.read_csv(metadata_path)
    
    # We expect 'transcript' or 'transcript_te' / etc in the CSV. Let's check:
    if 'transcript' not in df.columns:
        print("Warning: 'transcript' column not found. Checking for alternative names...")
        transcript_cols = [c for c in df.columns if 'transcript' in c.lower()]
        if transcript_cols:
            df['transcript'] = df[transcript_cols[0]]
        else:
            print("No transcript column found. Exiting.")
            return

    if sample_limit:
        df = df.head(sample_limit)
        print(f"Limiting to first {sample_limit} samples for testing.")

    results = []

    for index, row in df.iterrows():
        sample_id = row['sample_id']
        url = row.get('url', 'N/A')
        transcript = str(row.get('transcript', ''))
        
        # Original ground truth constraints from the sheet:
        reported_mla = row.get('Q1_MLA', 'N/A')
        reported_cm = row.get('Q3_Next_CM', 'N/A')
        reported_caste = row.get('Caste', 'N/A')
        reported_age = row.get('Age', 'N/A')
        reported_gender = row.get('Gender', 'N/A')

        if not transcript.strip() or transcript == "TRANSCRIPT_NOT_FOUND" or transcript == "READ_ERROR":
            results.append({
                "sample_id": sample_id,
                "audio_url": url,
                "classification_category": "4",
                "reason": "Fake Audio / Empty Audio - No transcript generated or missing audio."
            })
            continue

        system_prompt = """You are an expert Quality Control (QC) Auditor specializing in Tamil political surveys.
Your job is to read the transcribed Tamil audio context and evaluate it against the Reported Data submitted by the surveyor.

The audio transcript is from a political survey in Tamil Nadu.

Based on the rules provided below, carefully classify the sample into EXACTLY ONE of the following 5 categories.

### QC Disposition Guidelines

1) Correctly Done
• Correct: All main questions (MLA, CM, Gen/Age/Caste) were asked and responses generally match the data.
• Correct – Few Demographic Details Missed: Mobile/Name/Gender/Occupation/Age missing only if the enumerator asked and respondent refused.

2) Not Asking All Questions
• Few Political questions not asked.
• Caste question not asked.

3) Not Doing it Properly
• Wrong option selected (audio vs reported sheet mismatch).
• Respondent didn’t answer but enumerator filled on their own.
• Question meaning changed / paraphrased significantly.
• Leading / influencing answers.

4) Fake Audio / Empty Audio
• No interviewer & respondent voice (only traffic / TV / background noise).
• No respondent voice.
• Field staff interviewing each other.

5) Taking Samples from Friends & Relatives
• Mimicry / repeated voice pattern (hard to detect from text, but look for casual banter indicating they know each other intimately rather than a formal survey).

Analyze the alignment between Transcript and Reported Data. Be STRICT.
Return ONLY valid JSON with two fields:
- "classification_category": A string from "1", "2", "3", "4", "5" representing the rulebook category.
- "reason": A detailed comment explicitly mentioning what was missing, wrong, or why it matches the category.

Example JSON output:
{
  "classification_category": "2",
  "reason": "Caste and Age questions were not asked in the transcript."
}
"""

        user_content = f"""REPORTED DATA IN SHEET:
Q1 (MLA Performance): {reported_mla}
Q3 (Next CM): {reported_cm}
Caste: {reported_caste}
Age: {reported_age}
Gender: {reported_gender}

TRANSCRIPT (Tamil):
"{transcript}"
"""

        try:
            print(f"Classifying {sample_id}...")
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )

            result_txt = response.choices[0].message.content
            result_json = json.loads(result_txt)
            
            cat = result_json.get("classification_category", "Unknown")
            reason = result_json.get("reason", "No reason provided")
            
            # Additional logic to handle known edge cases if Cat is missing
            if cat not in ["1","2","3","4","5"]:
                cat = "3" # Default to not doing properly if LLM gets confused
                
            results.append({
                 "sample_id": sample_id,
                 "location": row.get('Location', 'Unknown'),
                 "audio_url": url,
                 "classification_category": cat,
                 "reason": reason
            })
            print(f" -> Category {cat}: {reason}")

        except Exception as e:
            print(f"Error evaluating {sample_id}: {e}")
            results.append({
                "sample_id": sample_id,
                "location": row.get('Location', 'Unknown'),
                "audio_url": url,
                "classification_category": "Unknown",
                "reason": f"Error during processing: {e}"
            })

    output_df = pd.DataFrame(results)
    
    # Optional: fetch original Location if missing from metadata
    excel_path = "/Users/aierarohit/Desktop/Political Data/Tamil Nadu/THIRUVOTTIYUR_2026-02-19_to_2026-02-20.xlsx"
    if os.path.exists(excel_path):
        excel_df = pd.read_excel(excel_path)
        if 'Location' in excel_df.columns and 'Sample ID' in excel_df.columns:
            loc_map = dict(zip(excel_df['Sample ID'], excel_df['Location']))
            output_df['location'] = output_df['sample_id'].map(loc_map)

    out_file = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'tn_audio_classification_results.csv')
    output_df.to_csv(out_file, index=False)
    print(f"\nCompleted! Saved results to {out_file}")

if __name__ == "__main__":
    limit = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        limit = int(sys.argv[1])
    classify_tn_audio(limit)
