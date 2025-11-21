import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import PyPDF2
import pandas as pd
import json
import time
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="NeuroLearn AI", page_icon="🧠", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Setup")
    api_key = st.text_input("Google Gemini API Key", type="password")
    st.caption("Get a key: [aistudio.google.com](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.info("Using **Gemini 1.5 Flash** (High Speed / High Free Quota)")

# --- FUNCTIONS ---

def clean_json_text(text):
    # Remove markdown and extract JSON object
    text = text.replace("```json", "").replace("```", "")
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != 0:
        return text[start:end]
    return text

def extract_pdf_text(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except:
        return None

def get_youtube_transcript(url):
    try:
        if "v=" in url: video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url: video_id = url.split("youtu.be/")[1]
        else: return None, "Invalid URL"
        
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return TextFormatter().format_transcript(transcript), None
    except Exception as e:
        return None, "Video must have captions enabled."

def analyze_content(content_text, api_key):
    genai.configure(api_key=api_key)
    
    # STRICT MODEL LIST: We only try models with generous free tiers.
    # We specifically avoid "experimental" (exp) models which have 0 quota.
    models_to_try = [
        'gemini-1.5-flash',       # Best option (Fastest, High Limits)
        'gemini-1.5-flash-001',   # Alternate ID
        'gemini-1.5-pro',         # Backup (Slower, but powerful)
        'gemini-pro'              # Legacy backup
    ]
    
    active_model = None
    
    # 1. Prompt
    prompt = f"""
    Analyze this content for a student using Cognitive Load Theory.
    Return strictly VALID JSON with no extra text:
    {{
        "summary": "2 sentence summary.",
        "difficulty_score": (Integer 1-10),
        "estimated_study_time_minutes": (Integer),
        "key_concepts": ["Concept1", "Concept2", "Concept3"],
        "learning_advice": "One specific study technique."
    }}
    
    CONTENT (Truncated):
    {content_text[:25000]}
    """

    # 2. Attempt with Priority List
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return json.loads(clean_json_text(response.text))
        except Exception as e:
            # If it's a quota error (429), wait 2 seconds and try next model
            if "429" in str(e):
                time.sleep(2)
                continue
            continue
            
    st.error("All AI models are busy or quota exceeded. Please try again in 1 minute.")
    return None

def generate_schedule(start_date, difficulty):
    intervals = [0, 1, 3, 7, 14, 30]
    schedule = []
    methods = ["📝 Blurting", "🗣️ Feynman", "🧩 Interleaving", "🧪 Application", "🔍 Analysis", "🏆 Review"] if difficulty > 6 else ["🧠 Recall", "⚡ Quiz", "🔄 Review", "🔗 Connections", "🎤 Teach", "✅ Check"]
    
    for i, days in enumerate(intervals):
        schedule.append({
            "Session": i + 1,
            "Date": (start_date + timedelta(days=days)).strftime("%Y-%m-%d"),
            "Technique": methods[i],
            "Focus": "Deep Work" if i < 2 else "Retention"
        })
    return pd.DataFrame(schedule)

# --- UI ---
st.title("🧠 NeuroSchedule AI")

if not api_key:
    st.warning("⚠️ Enter API Key in sidebar.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["PDF", "YouTube", "Text"])
content = None

with tab1:
    f = st.file_uploader("Upload PDF", type="pdf")
    if f: content = extract_pdf_text(f)
with tab2:
    u = st.text_input("YouTube URL")
    if u:
        t, e = get_youtube_transcript(u)
        if t: content = t
        else: st.error(e)
with tab3:
    t = st.text_area("Paste Text")
    if t: content = t

if content and st.button("🚀 Analyze"):
    with st.spinner("Connecting to AI Brain..."):
        data = analyze_content(content, api_key)
        if data:
            c1, c2 = st.columns(2)
            c1.metric("Difficulty", f"{data['difficulty_score']}/10")
            c2.metric("Time", f"{data['estimated_study_time_minutes']} min")
            st.info(data['summary'])
            st.write("**Concepts:** " + ", ".join(data['key_concepts']))
            st.success(f"💡 **Tip:** {data['learning_advice']}")
            st.dataframe(generate_schedule(datetime.now(), data['difficulty_score']), use_container_width=True, hide_index=True)
