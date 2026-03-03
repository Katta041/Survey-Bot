# API Intelligence Ecosystem 🎙️🗳️📡

A production-grade, modular suite of Streamlit applications designed for high-resolution political data analysis, audio transcription, and real-time observability.

## 🚀 Overview
This repository contains a unified ecosystem for processing citizen surveys and generating political insights. It bridges the gap between raw ground-level audio data and actionable intelligence for political campaigns.

### The Problem
Political surveys often produce thousands of audio recordings that are manually transcribed and analyzed, leading to high costs, human error, and slow turnaround.

### Our Solution
- **High-Speed Transcription**: Leverages Sarvam AI for extremely fast and accurate Tamil-to-Tamil transcription.
- **Deep Analysis**: Uses OpenAI GPT-4o for entity extraction, sentiment analysis, and thematic reporting.
- **conversational Intelligence**: Provides a chatbot interface to query thousands of transcripts using natural language.
- **Infrastructure Governance**: A centralized telemetry layer tracks every API call, token, and penny spent.

---

## 📁 Project Structure

```text
.
├── apps/                   # Streamlit Application Entry Points
│   ├── audio_transcription/# Processor for raw audio files
│   ├── survey_chatbot/     # Intelligence interface for survey data
│   └── dashboard/          # Enterprise Observability UI
├── src/                    # Core Business Logic & Shared Utilities
│   ├── core/               # Configuration, Telemetry, and DB Management
│   ├── logic/              # Transcription, Validation, and Reporting processors
│   └── utils/              # File handling, Audio processing, and Excel helpers
├── scripts/                # Data pipelines and developer utilities
├── data/                   # Persistent Storage (Ignored by Git)
│   ├── db/                 # SQLite Telemetry Databases
│   ├── raw/                # Source CSVs and Excel files
│   ├── results/            # Generated Markdown and PDF reports
│   └── audio_samples/      # Locally cached wav/mp3 files
├── assets/                 # Brand assets, logos, and static resources
└── tests/                  # Automated verification & validation scripts
```

---

## 🛠️ Setup & Installation

### 1. Prerequisites
- Python 3.9 or higher.
- `pip` package manager.
- Access to OpenAI and Sarvam AI APIs.

### 2. Physical Installation
```bash
git clone <repository-url>
cd political-data-ecosystem
pip install -r requirements.txt
```

### 3. Configuration & Secrets
We use a centralized configuration system located in `src/core/config.py`. 

#### Security Policy:
- **No hardcoded keys**: Keys are never committed to the repository.
- **Environment variables**: Priorities are given to system environment variables.
- **Local `.env`**: For local development, create a `.env` file in the root directory (automatically ignored by git):

```env
OPENAI_API_KEY=your_openai_key
SARVAM_API_KEY=your_sarvam_key
```

---

## 🖥️ The Application Suite

### 1. Audio Insight Engine (`apps/audio_transcription/app.py`)
Processing pipeline for raw audio recordings.
- **Input**: Public URLs or local file uploads.
- **Action**: Transcription (Sarvam) -> Refinement -> Synthesis (OpenAI).
- **Features**: Real-time progress tracking, batch mode support, and download of structured summaries.

### 2. Survey Chatbot TN (`apps/survey_chatbot/app.py`)
Natural language interface for deep-diving into survey results.
- **Engine**: Hybrid Search + LLM Reasoning.
- **Capabilities**:
    - "How many people in Vanniyar caste support TVK?"
    - "Why do people want to change the MLA?"
    - "Summarize sentiment toward the current CM."
- **Data**: Connects directly to `data/raw/` transcribed metadata.

### 3. Observability Dashboard (`apps/dashboard/app.py`)
The "Command Center" for the ecosystem.
- **Visuals**: Datadog-inspired dark mode UI.
- **Metrics tracked**:
    - **Total Spend**: Per-app and per-model cost aggregation.
    - **Request Volume**: Time-series analysis of API load.
    - **Latency Distribution**: Histograms of request speeds.
    - **Trace Log**: Full request/response previews for debugging.

---

## 🏗️ Technical Architecture

### Centralized Config (`src/core/config.py`)
Uses `pathlib` for absolute path normalization across MacOS, Linux, and Windows. This ensures that the application behaves identically regardless of where it is run.

### Telemetry System (`src/core/telemetry.py`)
A custom lightweight monitoring implementation:
- **`Span` Context Manager**: Measures sub-millisecond latency for critical segments.
- **SQLite Backend**: Efficient, local-first storage.
- **Non-blocking storage**: Telemetry writes happen in separate threads to avoid impacting user-facing UI performance.

### Data Normalization
All apps pull from the `data/` directory. If the directory is missing, the `Config` class automatically generates the required subfolders on the first run.

---

## 🧪 Development & Maintenance

### Running Benchmarks
Use `scripts/benchmarks/` to test transcription accuracy or LLM latency.
```bash
python scripts/benchmarks/test_intensive.py
```

### Verification
Run verification scripts before deploying changes:
```bash
python tests/test_search_logic.py
```

### Logs
System logs and dashboard execution logs are captured in `scripts/old/*.log` (configurable).

---

## 📜 Privacy & Security
- **PII Protection**: Audio recordings are processed in ephemeral buffers (where possible) and metadata is anonymized within the chatbot interface.
- **Secret Scrubbing**: A security audit has been performed to ensure no keys populate the git history.
- **Ignore Logic**: The `.gitignore` is configured to ignore all database files, environment variables, and raw data files to prevent accidental leakage of sensitive political data.

---
**Maintained by**: AI Intelligence Team
**Status**: Production Ready & Optimized
