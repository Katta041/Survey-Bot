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
        You are a data analyst assistant for a political survey dataset in Tamil Nadu.
        The dataset has columns: 
        - `MLA_Satisfaction` (Are you satisfied with the MLA?)
        - `Desires_Change` (Do you feel a change in govt is needed?)
        - `Next_CM` (Whom do you support as next CM?)
        - `Vote_2026` (Which party will you vote for?)
        - `Caste`, `Age_Group`, `Gender`
        - `QC Comment`
        - `transcript` (Tamil Audio Transcript)
        
        ### DATASET VOCABULARY (Colloquial Tamil Terms):
        - **Infrastructure:**
          - Roads: "சாலை" (Road), "ரோடு" (Road), "குழிகள்" (Potholes)
          - Water: "தண்ணீர்" (Water), "குடிநீர்" (Drinking Water), "குழாய்" (Tap)
          - Power: "மின்சாரம்" (Electricity), "கரண்ட்" (Current)
        - **Schemes:**
          - "திட்டம்" (Scheme), "உதவித்தொகை" (Pension), "ரேஷன்" (Ration)
        - **Leaders & Parties:**
          - "திமுக" (DMK), "அதிமுக" (ADMK), "விஜய்" (Vijay), "த.வெ.க" (TVK), "ஸ்டாலின்" (Stalin), "எடப்பாடி" (Edappadi)
          - "எம்.எல்.ஏ" (MLA), "முதல்வர்" (CM), "கட்சி" (Party)
        - **Sentiment:**
          - Positive: "நல்லா இருக்கு" (Good), "பரவாயில்லை" (Okay/Not bad), "திருப்தி" (Satisfied)
          - Negative: "மோசம்" (Bad), "திருப்தி இல்லை" (Not satisfied)
          - Change: "மாற்றம் தேவை" (Need change), "வேண்டாம்" (Don't want)

        ### SCHEMA MAPPING:
        - **Caste:** {unique_castes}
        - **Next_CM:** {unique_next_cm}
        - **Vote_2026:** {unique_vote}
        
        Current User Query: "{user_query}"
        Output Language: {lang}
        Previous Context: {history[-3:] if history else "None"}

        DECISION LOGIC:
        1. If the user asks for a COUNT, AGGREGATION, or STATISTIC: Return {{"type": "code", "code": "..."}}
        2. If the user asks for QUALITATIVE info: Return {{"type": "search", "keywords": ["..."], "topic": "..."}}
        3. If the user asks for MORE info on previous topic: Return {{"type": "more_results"}}
        4. If general chat: Return {{"type": "chat", "response": "..."}}
        
        Output MUST be valid JSON.
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
        matches = self.df[mask]
        
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
            f"- Do NOT mention 'code execution' or 'dataframe'.\n"
            f"- Just state the answer clearly."
        )
        try:
            res = self.client.chat.completions.create(
                model=Config.LLM_MODEL,
                messages=[{"role": "user", "content": final_prompt}]
            )
            return res.choices[0].message.content
        except Exception as e:
            return f"Answer naturalization failed: {e}"
