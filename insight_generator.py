import pandas as pd
import json
import time
import openai
import os

# --- SETUP ---
try:
    from framework_config import OPENAI_API_KEY
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
except:
    print("API Key missing")
    exit()

DATA_PATH = "/Users/aierarohit/Desktop/Political Data/audio_samples/transcribed_metadata_sarvam.csv"
try:
    df = pd.read_csv(DATA_PATH)
except:
    print("Could not load data")
    exit()

# Filter/Setup (Simplified integration from chatbot)
df['transcript'] = df['transcript'].astype(str)
if 'sample_id' not in df.columns:
    df['sample_id'] = df.index.astype(str)

# --- LOGIC REPLICATION (Simplified from survey_chatbot.py) ---

def search_transcripts(keywords, topic, df):
    # FALLBACK: Keyword Mapping (Copied from chatbot)
    english_to_telugu = {
        # --- PARTIES & LEADERS ---
        "ysrcp": ["YSRCP", "వైసిపి", "ఫ్యాన్", "జగన్"],
        "tdp": ["TDP", "టిడిపి", "సైకిల్", "బాబు", "చంద్రబాబు"],
        "jsp": ["JSP", "జనసేన", "పవన్", "గ్లాస్"],
        "jagan": ["జగన్", "జగనన్న", "CM"],
        "babu": ["బాబు", "చంద్రబాబు", "CBN"],
        "pawan": ["పవన్", "కళ్యాణ్"],
        "mla": ["ఎమ్మెల్యే", "నాయకుడు", "గొల్లపల్లి"],
        "incharge": ["ఇంచార్జ్", "సూర్యారావు"],

        # --- PERFORMANCE & SENTIMENT ---
        "performance": ["పనితీరు", "బాగుంది", "బాగోలేదు", "చేస్తున్నారు"],
        "good": ["బాగుంది", "మంచి", "సూపర్", "పర్లేదు"],
        "bad": ["బాగోలేదు", "చెత్త", "వెస్ట్", "రాదు"],
        "change": ["మార్చాలి", "వద్దు", "ఓడిపోతారు"],
        "win": ["గెలుస్తారు", "గెలుపు"],

        # --- INFRASTRUCTURE ---
        "roads": ["రోడ్లు", "రోడ్డు", "గుంతలు", "దారి"],
        "water": ["నీరు", "త్రాగునీరు", "మంచినీరు", "కొళాయి", "సమస్య"],
        "power": ["కరెంట్", "లైటు", "స్తంభం", "వెలుగు"],
        "drainage": ["డ్రైనేజ్", "కాలువ", "మురికి"],
        "housing": ["ఇల్లు", "స్థలాలు", "కాలనీ", "జగనన్న కాలనీ"],

        # --- SCHEMES ---
        "pension": ["పెన్షన్", "పింఛన్", "చెస్ట్"],
        "scheme": ["పథకం", "లబ్ది", "అర్హత"],
        "ration": ["రేషన్", "బియ్యం", "కందిపప్పు"],
        "amma vodi": ["అమ్మ ఒడి"],
        "cheyutha": ["చేయూత"],
        "vidya deevena": ["విద్యా దీవెన", "ఫీజు"],
        "rythu": ["రైతు", "భరోసా"],
        "volunteer": ["వాలంటీర్", "వాలంటీర్లు"],
        "secretariat": ["సచివాలయం", "ఆఫీసు"],

        # --- ISSUES ---
        "money": ["డబ్బు", "లంచం", "రేట్లు"],
        "corruption": ["లంచం", "డబ్బు", "కమిషన్"],
        "jobs": ["ఉద్యోగం", "పని", "కూలి"],
        "prices": ["ధరలు", "రేట్లు"]
    }
    
    expanded_keywords = set(keywords)
    for k in keywords:
        k_lower = k.lower()
        for eng_key, tel_vals in english_to_telugu.items():
            if eng_key in k_lower:
                expanded_keywords.update(tel_vals)
    keywords = list(expanded_keywords)

    mask = df['transcript'].str.contains('|'.join(keywords), case=False, na=False)
    matches = df[mask]
    
    if matches.empty:
        return None, []

    matches['length'] = matches['transcript'].str.len()
    matches = matches.sort_values('length', ascending=False)
    
    # 3 Samples max
    sample_matches = matches.head(3)
    context_text = ""
    citations = []
    
    for idx, row in sample_matches.iterrows():
        sid = row.get('sample_id', str(idx))
        text = row['transcript']
        if len(text) > 1500:
            text = text[:1500] + "... (truncated)"
        context_text += f"[Sample {sid}]: {text}\n\n"
        citations.append(sid)
        
    return context_text, citations

def synthesize_qualitative_answer(query, context):
    prompt = f"""
    User Query: {query}
    Context (Telugu Transcripts):
    {context}
    
    Task: Summarize the opinions/information found in these transcripts regarding the query.
    - The transcripts are in Telugu.
    - Identify key complaints, praises, or issues.
    - Cite the source using [Sample ID].
    - Answer in English (for the report).
    - If the context mentions the topic but has no clear opinion, state that.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def generate_full_response(query):
    # 1. Decision (Mock logic or use Prompt)
    # Using the Chatbot System Prompt for Decision
    
    system_prompt = """
    You are a data analyst assistant.
    If the user asks for QUALITATIVE info/feedback/opinion:
       - Return a JSON object with: {"type": "search", "keywords": ["..."], "topic": "..."}
       - Keywords should be Telugu terms if possible.
    """
    
    try:
        dec_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt}, # simplified prompt
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"}
        )
        decision = json.loads(dec_resp.choices[0].message.content)
        
        if decision.get("type") == "search":
            keywords = decision.get("keywords", [])
            topic = decision.get("topic", "")
            context, citations = search_transcripts(keywords, topic, df)
            
            if context:
                final_ans = synthesize_qualitative_answer(query, context)
                return final_ans, citations
            else:
                return f"No transcripts found for keywords: {keywords}", []
        return "Not a qualitative query (skipped)", []

    except Exception as e:
        return f"Error: {e}", []


# --- COMPLEX QUESTIONS ---
questions = [
    "What are the major complaints regarding Infrastructure (Roads, Water, Power)?",
    "How is the performance of the MLA? Provide specific positive and negative feedback.",
    "Is there corruption or bribery reported in welfare schemes? Give examples.",
    "What is the feedback on the Volunteer system? Are they helpful?",
    "Why are people unhappy with the current Incharge? What are the reasons for wanting a change?",
    "Summarize the sentiment towards Jagan (CM). Is it mostly positive or negative?",
    "What are the key issues faced by the Kapu community?"
]

print(f"Generating Report Insights for {len(questions)} questions...")
print("="*60)

report_content = "# Insight Report: Political Survey Data\n\n"

for i, q in enumerate(questions):
    print(f"Processing Q{i+1}: {q}")
    ans, cits = generate_full_response(q)
    
    print(f" -> Generated {len(ans)} chars.")
    
    report_content += f"## Q{i+1}: {q}\n\n"
    report_content += f"**Analysis:**\n{ans}\n\n"
    report_content += f"**Core Evidence:** {', '.join(cits)}\n\n"
    report_content += "---\n\n"
    
    time.sleep(1) # Rate limit safety

# Save
with open("report_insights.md", "w") as f:
    f.write(report_content)

print("="*60)
print("Report saved to report_insights.md")
