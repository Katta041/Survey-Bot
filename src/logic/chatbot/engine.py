import pandas as pd
import openai
import json
import datetime
from src.core.config import Config
from src.core.telemetry import Span, log_llm_call

class SurveyChatEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)

    def generate_decision(self, user_query: str, lang: str, history: list):
        """Asks LLM to decide on the query type (code, search, chat)."""
        unique_castes = self.df['Caste'].unique().tolist() if 'Caste' in self.df.columns else []
        unique_next_cm = self.df['Next_CM'].unique().tolist() if 'Next_CM' in self.df.columns else []
        unique_vote = self.df['Vote_2026'].unique().tolist() if 'Vote_2026' in self.df.columns else []
        
        system_prompt = f"""
You are a data analyst assistant for a Tamil Nadu political survey dataset (Thiruvottiyur constituency).
The pandas DataFrame is called `df` and has these columns:
- `MLA_Satisfaction` — MLA satisfaction response (string values)
- `Desires_Change`   — Whether govt change is needed (string values)
- `Next_CM`         — Whom they support as next CM (string values)
- `Vote_2026`       — Which party they plan to vote (string values)
- `Caste`           — Caste of respondent
- `Age_Group`       — Age group
- `Gender`          — Gender
- `Occupation`      — Occupation
- `transcript`      — Tamil audio transcript text
- `qc_comment`      — QC reviewer comment

### ACTUAL DATA VALUES:
- **Next_CM unique values:** {unique_next_cm}
- **Vote_2026 unique values:** {unique_vote}
- **Caste unique values:** {unique_castes}

### DECISION RULES — follow these STRICTLY:

**Use `code` type for ANY question about:**
- "who do people support / vote for / prefer"
- "how many", "what percentage", "count", "breakdown"
- "are people satisfied / happy / unhappy"
- "do people want change"
- specific candidate or party comparisons
- demographics (by caste, gender, age)
→ Return: {{"type": "code", "code": "<valid pandas expression that computes the answer>"}}

**Use `search` type for:**
- "what do people say about X" (qualitative opinions)
- "why do people support X"
- "what are people's concerns about X"
→ Return: {{"type": "search", "keywords": ["..."], "topic": "..."}}

**Use `more_results` type for:**
- "show me more", "give more examples"

**Use `chat` type ONLY for:**
- greetings, meta questions about the chatbot itself
- questions completely unrelated to the survey data

### EXAMPLES:
Q: "Who do people support for next CM?" → {{"type": "code", "code": "df['Next_CM'].value_counts()"}}
Q: "Are people satisfied with the MLA?" → {{"type": "code", "code": "df['MLA_Satisfaction'].value_counts()"}}
Q: "Which party will people vote for?" → {{"type": "code", "code": "df['Vote_2026'].value_counts()"}}
Q: "Do people want a change in government?" → {{"type": "code", "code": "df['Desires_Change'].value_counts()"}}
Q: "How many Vanniyar respondents support Vijay?" → {{"type": "code", "code": "df[df['Caste']=='Vanniyar']['Next_CM'].value_counts()"}}
Q: "What do people say about roads?" → {{"type": "search", "keywords": ["சாலை", "ரோடு", "road"], "topic": "roads infrastructure"}}
Q: "What are people's concerns?" → {{"type": "search", "keywords": ["மோசம்", "பிரச்சனை", "problem", "issue"], "topic": "citizen concerns"}}

Current User Query: "{user_query}"
Output Language: {lang}
Previous Context: {history[-3:] if history else "None"}

CRITICAL: Output ONLY valid JSON. No explanation. No markdown. Just JSON.
        """
        
        try:
            with Span() as span:
                response = self.client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query}
                    ],
                    response_format={"type": "json_object"}
                )
                u = response.usage
                log_llm_call(
                    app_name="survey_chatbot_tn",
                    user_query=user_query[:400],
                    response=response.choices[0].message.content[:300],
                    model=Config.LLM_MODEL,
                    input_tokens=u.prompt_tokens if u else 0,
                    output_tokens=u.completion_tokens if u else 0,
                    latency_ms=span.latency_ms,
                    query_type="decision",
                )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"type": "error", "message": f"Decision error: {str(e)}"}

    def execute_code(self, code: str):
        """Executes generated Pandas code safely."""
        try:
            local_vars = {"df": self.df, "pd": pd}
            # Try evaluating as a single expression first
            try:
                result = eval(code, {}, local_vars)
                return result
            except SyntaxError:
                exec(code, {}, local_vars)
                if 'result' in local_vars:
                    return local_vars['result']
                # Fallback to last defined var
                result = None
                for key, val in reversed(list(local_vars.items())):
                    if key not in ['df', 'pd'] and not isinstance(val, type(pd)):
                        result = val
                        break
                return result
        except Exception as e:
            return f"Error executing code: {e}"

    def search_transcripts(self, keywords: list, topic: str, exclude_ids: list = []):
        """Searches transcripts for keywords and returns context for LLM."""
        mask = self.df['transcript'].str.contains('|'.join(keywords), case=False, na=False)
        matches = self.df[mask].copy()
        
        if exclude_ids:
            matches = matches[~matches['sample_id'].isin(exclude_ids)]
        
        if matches.empty:
            return None, [], 0
        
        matches['length'] = matches['transcript'].str.len()
        matches = matches.sort_values('length', ascending=False)
        
        total_matches = len(matches)
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
            
        return context_text, citations, total_matches

    def synthesize_answer(self, query: str, context: str, lang: str):
        """Uses LLM to synthesize a natural answer from search results."""
        prompt = f"""
        User Query: {query}
        Context (Tamil Transcripts):
        {context}
        
        Task: Summarize the opinions/information found in these transcripts regarding the query.
        - The transcripts are in Tamil.
        - Cite the source using [Sample ID] for every point.
        - Answer in: {lang}
        - If context is empty or irrelevant, state that clearly.
        """
        try:
            with Span() as span:
                response = self.client.chat.completions.create(
                    model=Config.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}]
                )
                u = response.usage
                log_llm_call(
                    app_name="survey_chatbot_tn",
                    user_query=query[:400],
                    response=response.choices[0].message.content[:300],
                    model=Config.LLM_MODEL,
                    input_tokens=u.prompt_tokens if u else 0,
                    output_tokens=u.completion_tokens if u else 0,
                    latency_ms=span.latency_ms,
                    query_type="qualitative_synthesis",
                )
            return response.choices[0].message.content
        except Exception as e:
            return f"Synthesis error: {str(e)}"

    def naturalize_data_answer(self, query: str, data: str, lang: str):
        """Turns raw data (numbers/dicts) into natural language."""
        final_prompt = (
            f"User Question: '{query}'\n"
            f"Data Result: {data}\n"
            f"Task: Respond to the user naturally in {lang}.\n"
            f"- Present the data clearly, using percentages or counts where helpful.\n"
            f"- Do NOT mention 'code execution' or 'dataframe'.\n"
            f"- Just state the answer clearly and concisely."
        )
        try:
            res = self.client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[{"role": "user", "content": final_prompt}]
            )
            return res.choices[0].message.content
        except Exception as e:
            return f"Answer naturalization failed: {e}"
