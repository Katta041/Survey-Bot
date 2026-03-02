import streamlit as st
import pandas as pd
import openai
import os
import io
import requests
import av
from pydub import AudioSegment
from sarvamai import SarvamAI
import json

# --- Configuration ---
st.set_page_config(page_title="AI Audio Insight Engine", page_icon="🎙️", layout="wide")

# --- Custom CSS for Professional Look ---
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #f7f9fc;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1e3a8a;
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards for summary */
    .summary-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-top: 4px solid #3b82f6;
    }
    
    .pro-card { border-top-color: #10b981; }
    .con-card { border-top-color: #ef4444; }
    .neutral-card { border-top-color: #8b5cf6; }
</style>
""", unsafe_allow_html=True)

# --- API Keys Management ---
# Handles local runs with framework_config or Streamlit Community Cloud with st.secrets
def get_api_key(secret_name):
    try:
        if secret_name in st.secrets:
            return st.secrets[secret_name]
    except Exception:
        pass  # Fallback to local config if secrets file is missing

    try:
        import framework_config
        return getattr(framework_config, secret_name)
    except (ImportError, AttributeError):
        return None

openai_api_key = get_api_key("OPENAI_API_KEY")
sarvam_api_key = get_api_key("SARVAM_API_KEY")

if not openai_api_key or not sarvam_api_key:
    st.error("🔑 API Keys Missing! Please add OPENAI_API_KEY and SARVAM_API_KEY to `.streamlit/secrets.toml` or `framework_config.py`.")
    st.stop()

# Initialize Clients
os.environ["OPENAI_API_KEY"] = openai_api_key
openai_client = openai.OpenAI(api_key=openai_api_key)
sarvam_client = SarvamAI(api_subscription_key=sarvam_api_key)


# --- Helper Functions ---
def load_audio_wav_bytes(file_or_bytes):
    """Converts input audio file/bytes to 16kHz mono WAV bytes for Sarvam API."""
    try:
        container = av.open(file_or_bytes)
        audio_stream = container.streams.audio[0]
        
        # Resample to 16kHz mono
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        output_buffer = io.BytesIO()
        output_container = av.open(output_buffer, mode='w', format='wav')
        output_stream = output_container.add_stream('pcm_s16le', rate=16000, layout='mono')
        
        for frame in container.decode(audio_stream):
            frame.pts = None
            resampled_frames = resampler.resample(frame)
            for r_frame in resampled_frames:
                for packet in output_stream.encode(r_frame):
                    output_container.mux(packet)
                    
        # Flush the resampler
        resampled_frames = resampler.resample(None)
        if resampled_frames:
             for r_frame in resampled_frames:
                for packet in output_stream.encode(r_frame):
                    output_container.mux(packet)

        for packet in output_stream.encode(None): # Flush stream
            output_container.mux(packet)
            
        output_container.close()
        return output_buffer.getvalue()
    except Exception as e:
        st.error(f"Error processing audio layout: {e}")
        return None

@st.spinner("Transcribing audio using Sarvam AI...")
def transcribe_audio(wav_bytes):
    """Hits the Sarvam API with the given WAV bytes. Chunks audio if >28 seconds."""
    
    # Use pydub to split the buffer
    # pydub can read wav directly from bytes
    audio_segment = AudioSegment.from_wav(io.BytesIO(wav_bytes))
    
    # Sarvam has a 30s limit. We chunk at 28s just to be safe.
    chunk_length_ms = 28000
    chunks = []
    
    for i in range(0, len(audio_segment), chunk_length_ms):
        chunks.append(audio_segment[i:i + chunk_length_ms])

    full_transcript = []
    
    progress_text = "Transcribing chunk {} of {}..."
    my_bar = st.progress(0, text=progress_text.format(1, len(chunks)))

    for i, chunk in enumerate(chunks):
        my_bar.progress((i) / len(chunks), text=progress_text.format(i + 1, len(chunks)))
        
        # Export chunk back to WAV bytes
        chunk_buffer = io.BytesIO()
        chunk.export(chunk_buffer, format="wav")
        chunk_bytes = chunk_buffer.getvalue()
        
        try:
            result = sarvam_client.speech_to_text.transcribe(
                file=chunk_bytes,
                model="saaras:v3",
                language_code="ta-IN", 
                mode="transcribe"
            )
            if result.transcript:
                full_transcript.append(result.transcript.strip())
        except Exception as e:
            st.error(f"Transcription failed on chunk {i+1}: {str(e)}")
            return None
            
    my_bar.empty()
    return " ".join(full_transcript)

@st.spinner("Analyzing transcript using LLM...")
def analyze_transcript(transcript):
    """Uses OpenAI to extract structured political insights."""
    prompt = f"""
    You are an expert political analyst and a professional Tamil-to-English translator. 
    Below is a transcript of a citizen from Tamil Nadu speaking in Tamil.
    
    Transcript:
    "{transcript}"
    
    Read the transcript carefully. Your first task is to provide a highly accurate, natural-sounding English translation. 
    Pay close attention to local Tamil political context, idioms, and sentiment. Do not output any Telugu or mix languages.
    
    Then, extract the following insights and respond strictly in JSON format matching the schema below:
    {{
        "english_translation": "A highly accurate, natural-sounding English translation of the entire transcript",
        "supporting_party": "Name of the party or 'Neutral/Unknown'",
        "overall_sentiment": "Positive/Negative/Neutral",
        "pros": ["Point 1", "Point 2"],
        "cons": ["Point 1", "Point 2"],
        "key_issues": ["Issue 1", "Issue 2"],
        "summary": "A 2-3 sentence summary of what the citizen is saying."
    }}
    
    Ensure the JSON is valid.
    """
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Analysis failed: {str(e)}")
        return None

# --- Main App ---
st.title("🎙️ Political Insight Audio Engine")
st.markdown("Upload a citizen survey audio recording or provide a URL to instantly get a transcription and structured political analysis.")

st.markdown("---")

# Input Method Selection
input_mode = st.radio("Select Input Method:", ["Upload Audio File", "Paste Audio URL"], horizontal=True)

audio_file = None
audio_bytes_raw = None

if input_mode == "Upload Audio File":
    uploaded_file = st.file_uploader("Upload Audio (MP3, WAV, M4A, OGG)", type=["mp3", "wav", "m4a", "ogg"])
    if uploaded_file is not None:
        audio_bytes_raw = uploaded_file.read()
        audio_file = io.BytesIO(audio_bytes_raw)
        
elif input_mode == "Paste Audio URL":
    audio_url = st.text_input("Enter Audio URL:")
    if audio_url:
        try:
            response = requests.get(audio_url)
            if response.status_code == 200:
                audio_bytes_raw = response.content
                audio_file = io.BytesIO(audio_bytes_raw)
                st.success("Audio loaded from URL successfully!")
            else:
                st.error("Failed to fetch audio from URL. Please check the link.")
        except Exception as e:
            st.error(f"Error fetching URL: {e}")

# Process and Display
if audio_file:
    st.subheader("🎵 Audio Preview")
    st.audio(audio_bytes_raw, format='audio/wav')
    
    if st.button("🚀 Process Audio", type="primary", use_container_width=True):
        # 1. Conversion
        with st.status("Preprocessing Audio...", expanded=True) as status:
            st.write("Converting to 16kHz mono format...")
            # We need to seek to 0 before reading it into av
            audio_file.seek(0)
            wav_bytes = load_audio_wav_bytes(audio_file)
            
            if not wav_bytes:
                status.update(label="Audio preprocessing failed.", state="error")
                st.stop()
            st.write("Audio ready for transcription.")
            
            # 2. Transcription
            st.write("Transcribing via Sarvam Saaras:v3...")
            transcript = transcribe_audio(wav_bytes)
            if not transcript:
                status.update(label="Transcription failed.", state="error")
                st.stop()
            st.write("Transcription complete.")
            st.session_state.transcript_result = transcript
            
            # 3. LLM Analysis
            st.write("Generating AI insights...")
            analysis = analyze_transcript(transcript)
            if not analysis:
                status.update(label="Analysis failed.", state="error")
                st.stop()
            st.session_state.analysis_result = analysis
            st.write("Analysis complete!")
            
            status.update(label="Processing Complete!", state="complete", expanded=False)
        
        # Display Results
        st.markdown("---")
        st.header("📊 Audio Insights")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(f"""
            <div class="summary-card neutral-card" style="padding-bottom: 5px;">
                <h3 style="margin-bottom: 0;">📝 Transcript</h3>
            </div>
            """, unsafe_allow_html=True)
            
            tab1, tab2 = st.tabs(["Tamil (Original)", "English (Translation)"])
            
            with tab1:
                st.markdown(f"""
                <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">
                    <p style="font-size: 1.1em; line-height: 1.5; margin: 0;">{transcript}</p>
                </div>
                """, unsafe_allow_html=True)
            with tab2:
                display_translation = analysis.get('english_translation', 'Translation not available.')
                st.markdown(f"""
                <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);">
                    <p style="font-size: 1.1em; line-height: 1.5; margin: 0;">{display_translation}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="summary-card">
                <h3>🗣️ Executive Summary</h3>
                <p>{analysis.get('summary', 'N/A')}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            sentiment_map = {
                "Positive": "🟢",
                "Negative": "🔴",
                "Neutral": "⚪"
            }
            sentiment = analysis.get('overall_sentiment', 'Neutral')
            emoji = sentiment_map.get(sentiment, "⚪")
            
            st.markdown(f"""
            <div class="summary-card neutral-card">
                <h3>🏛️ Target Information</h3>
                <p><strong>Supporting Party:</strong> {analysis.get('supporting_party', 'N/A')}</p>
                <p><strong>Overall Sentiment:</strong> {emoji} {sentiment}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Pros
            pros_html = "".join([f"<li>{p}</li>" for p in analysis.get('pros', [])])
            if pros_html:
                st.markdown(f"""
                <div class="summary-card pro-card">
                    <h3>✅ Pros / Positive Points</h3>
                    <ul>{pros_html}</ul>
                </div>
                """, unsafe_allow_html=True)
                
            # Cons
            cons_html = "".join([f"<li>{c}</li>" for c in analysis.get('cons', [])])
            if cons_html:
                st.markdown(f"""
                <div class="summary-card con-card">
                    <h3>❌ Cons / Complaints</h3>
                    <ul>{cons_html}</ul>
                </div>
                """, unsafe_allow_html=True)
                
            # Key Issues
            issues_tags = "".join([f'<span style="background-color: #e2e8f0; padding: 5px 10px; border-radius: 15px; margin-right: 5px; display: inline-block; margin-bottom: 5px;">📍 {i}</span>' for i in analysis.get('key_issues', [])])
            if issues_tags:
                st.markdown(f"""
                <div class="summary-card neutral-card">
                    <h3>📌 Key Issues Highlighted</h3>
                    <div>{issues_tags}</div>
                </div>
                """, unsafe_allow_html=True)
