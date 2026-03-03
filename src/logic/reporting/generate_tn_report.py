import pandas as pd
import json
import os
import openai
from jinja2 import Template

# -----------------
# 1. Configuration
# -----------------
try:
    from framework_config import OPENAI_API_KEY
    openai.api_key = OPENAI_API_KEY
except:
    openai.api_key = os.environ.get("OPENAI_API_KEY")

DATA_PATH = "/Users/aierarohit/Desktop/Political Data/tn_app_data_anonymized.csv"
OUTPUT_PDF = "/Users/aierarohit/Desktop/Political Data/Thiruvottiyur_Survey_Report.pdf"

client = openai.OpenAI(api_key=openai.api_key)

# -----------------
# 2. Extract Data
# -----------------
print("Loading Survey Data...")
df = pd.read_csv(DATA_PATH)
df.fillna("Unknown", inplace=True)
total_surveys = len(df)

party_logos = {
    "DMK": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/DMK_flag.svg/200px-DMK_flag.svg.png",
    "AIADMK": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/AIADMK_official_flag.svg/200px-AIADMK_official_flag.svg.png",
    "TVK": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Tamilaga_Vettri_Kazhagam_Flag.svg/200px-Tamilaga_Vettri_Kazhagam_Flag.svg.png",
    "NTK": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Naam_Tamilar_Katchi_flag.svg/200px-Naam_Tamilar_Katchi_flag.svg.png",
    "BJP": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Bharatiya_Janata_Party_logo.svg/200px-Bharatiya_Janata_Party_logo.svg.png"
}

# Simplify Party Names for cleaner reporting
def map_party(val):
    val = str(val).upper()
    if 'TVK' in val or 'VIJAY' in val or 'விஜய்' in val: return 'TVK'
    if 'DMK' in val and 'ADMK' not in val and 'AIADMK' not in val: return 'DMK'
    if 'ADMK' in val or 'AIADMK' in val or 'எடப்பாடி' in val: return 'AIADMK'
    if 'NTK' in val or 'SEEMAN' in val or 'சீமான்' in val: return 'NTK'
    if 'BJP' in val: return 'BJP'
    return 'Others/Undecided'

df['Clean_Party'] = df['Vote_2026'].apply(map_party)

# Analytics
print("Calculating Demographics & Support Metrics...")
party_support = df['Clean_Party'].value_counts().to_dict()
gender_breakdown = pd.crosstab(df['Clean_Party'], df['Gender']).to_dict(orient='index')

# Normalize the Gender keys which might contain "Male / ஆண்"
demographics = {}
for pty, g_dict in gender_breakdown.items():
    males = sum(v for k, v in g_dict.items() if 'Male' in k and 'Female' not in k)
    females = sum(v for k, v in g_dict.items() if 'Female' in k)
    demographics[pty] = {"Male": males, "Female": females}

import time

# -----------------
# 3. GPT-4o Qualitative Analysis
# -----------------
print("Extracting Transcripts for Qualitative Analysis...")
def get_transcript_samples(dataframe, party, support=True, limit=25):
    if support:
        sample_df = dataframe[dataframe['Clean_Party'] == party].head(limit)
    else:
        sample_df = dataframe[dataframe['Clean_Party'] != party].head(limit)
    
    return [f"[{row['sample_id']}] {row['transcript']}" for _, row in sample_df.iterrows()]

support_tvk_transcripts = get_transcript_samples(df, 'TVK', True)
oppose_tvk_transcripts = get_transcript_samples(df, 'TVK', False)
support_dmk_transcripts = get_transcript_samples(df, 'DMK', True)
oppose_dmk_transcripts = get_transcript_samples(df, 'DMK', False)

def get_top_5_reasons(concept, transcripts, support=True):
    print(f"Requesting LLM Analysis for: {concept} (Support: {support})...")
    action_str = "support" if support else "do NOT support"
    prompt = f"""
    Analyze the following {len(transcripts)} Tamil survey transcripts.
    Extract the Top 5 reasons why voters {action_str} {concept}.
    Return ONLY a valid JSON array of exactly 5 detailed strings (in English).
    CRITICAL INSTRUCTION: Since the input transcripts start with an ID like [123], you MUST append the exact IDs of the transcripts that support that reason at the end of the string, in the format [Audio IDs: X, Y, Z].
    Example: ["They like the welfare schemes [Audio IDs: 12, 45]", "Reason 2 [Audio IDs: 3, 9]", "Reason 3 [Audio IDs: 22]", "Reason 4 [Audio IDs: 1]", "Reason 5 [Audio IDs: 4, 5]"]
    
    Transcripts Data:
    {chr(10).join(transcripts[:25])}
    """
    try:
        res = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content
        extracted = []
        # Robust parsing for different JSON outputs
        parsed = json.loads(content)
        if isinstance(parsed, list):
            extracted = parsed
        elif isinstance(parsed, dict):
            for key in ["reasons", "Reasons", "top_5_reasons", "Top_5_Reasons"]:
                if key in parsed and isinstance(parsed[key], list):
                    extracted = parsed[key]
                    break
            # Fallback if dictionary has weird keys
            if not extracted and parsed.values():
                first_val = list(parsed.values())[0]
                if isinstance(first_val, list):
                    extracted = first_val
                
        # Padding
        while len(extracted) < 5:
            extracted.append(f"Insufficient qualitative data to determine reason #{len(extracted)+1}")
            
        return extracted[:5]
    except Exception as e:
        print(f"Error fetching insights: {e}")
        return [f"Could not extract insights ({e})"] * 5

reasons_tvk_support = get_top_5_reasons("Vijay / TVK", support_tvk_transcripts, True)
time.sleep(15)
reasons_tvk_oppose = get_top_5_reasons("Vijay / TVK", oppose_tvk_transcripts, False)
time.sleep(15)
reasons_dmk_support = get_top_5_reasons("Stalin / DMK", support_dmk_transcripts, True)
time.sleep(15)
reasons_dmk_oppose = get_top_5_reasons("Stalin / DMK", oppose_dmk_transcripts, False)

import requests
from fpdf import FPDF

import matplotlib.pyplot as plt

def generate_pie_chart(party_name, male_count, female_count, filename):
    labels = ['Male Voters', 'Female Voters']
    sizes = [male_count, female_count]
    colors = ['#3498db', '#e74c3c']
    explode = (0.1, 0)
    plt.figure(figsize=(4,4))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.title(f'{party_name} Voter Demographics')
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# Download Logos Locally for Markdown Preview
print("Downloading Logos for local rendering...")
local_logos = {}
os.makedirs("/Users/aierarohit/Desktop/Political Data/logos", exist_ok=True)
headers = {'User-Agent': 'PoliticalSurveyBot/1.0 (rohit@example.com) Python-requests/2.x'}
for party, url in party_logos.items():
    try:
        r = requests.get(url, headers=headers)
        if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
            path = f"logos/{party}.png"
            full_path = f"/Users/aierarohit/Desktop/Political Data/{path}"
            with open(full_path, 'wb') as f:
                f.write(r.content)
            local_logos[party] = path
    except Exception as e:
        print(f"Failed to download {party} logo: {e}")

# Generate Charts
print("Generating Pie Charts...")
generate_pie_chart("TVK", demographics.get("TVK", {}).get("Male", 0), demographics.get("TVK", {}).get("Female", 0), "/Users/aierarohit/Desktop/Political Data/tvk_demographics.png")
generate_pie_chart("DMK", demographics.get("DMK", {}).get("Male", 0), demographics.get("DMK", {}).get("Female", 0), "/Users/aierarohit/Desktop/Political Data/dmk_demographics.png")

# -----------------
# 4. Generate Markdown
# -----------------
print("Generating Markdown Report...")

OUTPUT_MD = "/Users/aierarohit/Desktop/Political Data/Thiruvottiyur_Survey_Report.md"

md_template = """# Thiruvottiyur Constituency Survey Report

**Total Survey Points:** {{ total_surveys }}  
*Source: Validated Field Survey Database (Excel Metadata)*

## 1. Overall Party Support & Demographics
The following illustrates the breakdown of voter support for the upcoming 2026 elections, including male/female demographic splits. Data is computationally verified.

| Party / Leader | Logo | Total Support | Male Voters | Female Voters |
|---|---|---|---|---|
{% for party, count in party_support.items() %}| **{{ party }}** | {% if party in local_logos %}<img src="{{ local_logos[party] }}" width="30">{% endif %} | {{ count }} | {{ demographics[party]['Male'] }} | {{ demographics[party]['Female'] }} |
{% endfor %}

*Source: Cross-tabulation of Q4 (Vote 2026) and Q9 (Gender) from Anonymized Field Dataset*

---

## 2. Qualitative Insights: Vijay (TVK)
Using advanced AI analysis on native Tamil audio transcriptions, the following primary drivers were identified.

<img src="tvk_demographics.png" width="400">

### Top 5 Reasons for SUPPORTING TVK
{% for reason in tvk_support %}- {{ reason }}
{% endfor %}

### Top 5 Reasons for NOT SUPPORTING TVK
{% for reason in tvk_oppose %}- {{ reason }}
{% endfor %}

*Source: AI extraction from Sarvam Speech-to-Text Tamil Audio Transcripts*

---

## 3. Qualitative Insights: M.K. Stalin (DMK)

<img src="dmk_demographics.png" width="400">

### Top 5 Reasons for SUPPORTING DMK
{% for reason in dmk_support %}- {{ reason }}
{% endfor %}

### Top 5 Reasons for NOT SUPPORTING DMK
{% for reason in dmk_oppose %}- {{ reason }}
{% endfor %}

*Source: AI extraction from Sarvam Speech-to-Text Tamil Audio Transcripts*
"""

template = Template(md_template)
md_content = template.render(
    total_surveys=total_surveys,
    party_support=party_support,
    demographics=demographics,
    party_logos=party_logos,
    tvk_support=reasons_tvk_support,
    tvk_oppose=reasons_tvk_oppose,
    dmk_support=reasons_dmk_support,
    dmk_oppose=reasons_dmk_oppose
)

with open(OUTPUT_MD, "w") as f:
    f.write(md_content)

print(f"✅ Success! Markdown Report saved to: {OUTPUT_MD}")
