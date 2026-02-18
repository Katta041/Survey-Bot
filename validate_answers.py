import os
import json
import pandas as pd
from openai import OpenAI
import framework_config as config

client = OpenAI(api_key=config.OPENAI_API_KEY)

def validate_answers():
    transcript_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'transcribed_metadata.csv')
    if not os.path.exists(transcript_path):
        print("Transcript file not found. Run transcriber first.")
        return

    df = pd.read_csv(transcript_path)
    print(f"Validating {len(df)} records...")

    validation_results = []
    reasons = []

    for index, row in df.iterrows():
        sample_id = row['sample_id']
        transcript = str(row['transcript']) # Ensure string
        
        # Prepare data context for LLM
        # Focusing on Q1 (Problem), Age, Caste as key validation points
        data_context = f"""
        Sample ID: {sample_id}
        Reported Q1 (Main Problem): {row.get('Q1', 'N/A')}
        Reported Caste: {row.get('Caste', 'N/A')}
        Reported Age: {row.get('Age', 'N/A')}
        """

        prompt = f"""
        You are a Quality Control Auditor for a Telugu political survey.
        
        TASK:
        Compare the provided TELUGU TRANSCRIPT of the audio with the REPORTED DATA.
        Determine if the surveyor actually asked the questions and if the respondent's answers match the data.
        
        TRANSCRIPT (Telugu):
        "{transcript}"
        
        REPORTED DATA:
        {data_context}
        
        INSTRUCTIONS:
        1. Check if the transcript contains a conversation relevant to a survey.
        2. Check if the reported data (Problem, Caste, Age) is mentioned or consistent with the audio.
        3. If the audio is empty, noise, or irrelevant, mark as INVALID.
        4. If the surveyor fills data without asking (e.g. asking only name but filling caste/problems), mark as INVALID.
        
        OUTPUT FORMAT:
        Return ONLY a JSON object with two keys:
        - "is_valid": boolean (true/false)
        - "reason": string (brief explanation)
        """

        try:
            print(f"Validating {sample_id}...")
            response = client.chat.completions.create(
                model=config.VALIDATION_MODEL, # GPT-4o
                messages=[
                    {"role": "system", "content": "You are a precise data validator."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0
            )
            
            content = response.choices[0].message.content
            try:
                result = json.loads(content)
            except json.JSONDecodeError:
                # Fallback for simple cleanup if needed
                result = json.loads(content.replace("```json", "").replace("```", ""))

            is_valid = result.get('is_valid', False)
            reason = result.get('reason', 'No reason provided')
            
            print(f"Result: {is_valid} | {reason}")
            
            validation_results.append(is_valid)
            reasons.append(reason)
            
        except Exception as e:
            print(f"Error validating {sample_id}: {e}")
            validation_results.append(False)
            reasons.append(f"Error: {str(e)}")

    df['llm_is_valid'] = validation_results
    df['llm_reason'] = reasons
    
    output_path = os.path.join(config.AUDIO_DOWNLOAD_DIR, 'validation_results.csv')
    df.to_csv(output_path, index=False)
    print(f"Validation complete. Results saved to {output_path}")

if __name__ == "__main__":
    validate_answers()
