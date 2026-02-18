# 🗳️ Survey Data Intelligence Chatbot

A bilingual (English/Telugu) AI-powered chatbot designed to analyze political survey data. It combines structured data analysis (Pandas) with qualitative insight generation (LLM) to answer complex queries about voter sentiment, infrastructure issues, and leadership performance.

## 🌟 Features

-   **Bilingual Support:** Ask questions in **English** or **Telugu** (colloquial terms supported).
-   **Hybrid Intelligence:**
    -   **Quantitative:** "How many people voted for TDP?" (Executes Python code on dataset).
    -   **Qualitative:** "Why are people unhappy with the MLA?" (Semantic search on audio transcripts).
-   **Smart Pagination:** Ask "Anything else?" to get more results on the same topic.
-   **Robust Search:** Maps English keywords (e.g., "Roads", "Corruption") to local Telugu vocabulary (e.g., "Gathukulu", "Lancham").
-   **Audio Context:** Cites specific audio sample IDs for every insight.

## 🚀 How to Run

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set API Key:**
    -   Create a `secrets.toml` file in `.streamlit/` OR set it in `framework_config.py`.
    -   Key: `OPENAI_API_KEY`

3.  **Run the App:**
    ```bash
    streamlit run survey_chatbot.py
    ```

## 📂 Project Structure

-   `survey_chatbot.py`: Main Streamlit application.
-   `insight_generator.py`: Script for generating offline batch reports.
-   `requirements.txt`: Python dependencies.
-   `data/`: Contains survey datasets (Excel/CSV).

## 🛠️ Tech Stack

-   **Frontend:** Streamlit
-   **AI/LLM:** OpenAI GPT-4o
-   **Data:** Pandas, OpenPyXL
-   **Search:** Semantic keyword mapping & Pandas filtering

## 📢 Deployment

This app is ready for [Streamlit Community Cloud](https://streamlit.io/cloud).
1.  Push to GitHub.
2.  Connect repository.
3.  Add `OPENAI_API_KEY` in Streamlit Secrets.
