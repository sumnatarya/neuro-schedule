import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import PyPDF2
import pandas as pd
import json
from datetime import datetime, timedelta
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="NeuroLearn AI", page_icon="🧠", layout="wide")

# --- SESSION STATE ---
if "working_model_name" not in st.session_state:
    st.session_state.working_model_name = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Setup")
    api_key = st.text_input("Google Gemini API Key", type="password").strip()
    
    st.divider()
    status_box = st.empty()

# --- ROBUST FUNCTIONS ---

def find_working_model(api_key):
    """
    Tries every possible model name until one works.
    """
    genai.configure(api_key=api_key)
    
    # List of candidates to try (Newest -> Oldest)
    candidates = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-pro",
        "gemini-1.0-pro"
    ]
    
    status_box.info("🔍 Testing AI models...")
    
    for model_name in candidates:
        try:
            # Try to generate a tiny prompt to test connection
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Test")
            if response:
                return model_name
        except Exception as e:
            # If 404 (Not found) or 429 (Quota), just try the next one
            continue
            
    return None

def clean_json_text(text):
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
    except:
        return None, "Video must have captions enabled."

def analyze_content(content_text, api_key, model_name):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    Analyze this content for a student. Return strictly VALID JSON:
    {{
        "summary": "2 sentence summary.",
        "difficulty_score": (Integer 1-10),
        "estimated_study_time_minutes": (Integer),
        "key_concepts": ["Concept1", "Concept2", "Concept3"],
        "learning_advice": "One specific study technique."
    }}
    
    CONTENT:
    {content_text[:25000]}
    """
    
    try:
        response = model.generate_content(prompt)
        return json.loads(clean_json_text(response.text))
    except Exception as e:
        st.error(f"AI Error: {e}")
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

# --- MAIN LOGIC ---

# Check connection immediately
if api_key:
    if not st.session_state.working_model_name:
        found_model = find_working_model(api_key)
        if found_model:
            st.session_state.working_model_name = found_model
            status_box.success(f"✅ Connected: `{found_model}`")
        else:
            status_box.error("❌ No working models found. Check Quota/Key.")
    else:
        status_box.success(f"✅ Using: `{st.session_state.working_model_name}`")

st.title("🧠 NeuroSchedule AI")

if not st.session_state.working_model_name:
    st.warning("waiting for valid API connection...")
    st.stop()

tab1, tab2, tab3 = st.tabs(["📄 PDF Upload", "📺 YouTube Video", "📝 Paste Text"])
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
    with st.spinner("Analyzing..."):
        data = analyze_content(content, api_key, st.session_state.working_model_name)
        if data:
            st.divider()
            c1, c2 = st.columns(2)
            c1.metric("Difficulty", f"{data['difficulty_score']}/10")
            c2.metric("Time", f"{data['estimated_study_time_minutes']} min")
            st.info(data['summary'])
            st.write("**Concepts:** " + ", ".join(data['key_concepts']))
            st.success(f"💡 **Tip:** {data['learning_advice']}")
            st.dataframe(generate_schedule(datetime.now(), data['difficulty_score']), use_container_width=True, hide_index=True)
