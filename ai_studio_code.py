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
    # .strip() removes accidental spaces when pasting
    api_key_input = st.text_input("Google Gemini API Key", type="password")
    api_key = api_key_input.strip() if api_key_input else None
    
    st.caption("Get a key: [aistudio.google.com](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.write("### 🛠️ Diagnostics")
    debug_placeholder = st.empty()

# --- FUNCTIONS ---

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
    except Exception as e:
        return None, "Video must have captions enabled."

def get_working_model(api_key):
    """
    Asks Google specifically which models are allowed for this Key.
    """
    genai.configure(api_key=api_key)
    try:
        # 1. List all models available to this key
        all_models = list(genai.list_models())
        
        # 2. Filter for models that generate content
        generative_models = [m for m in all_models if 'generateContent' in m.supported_generation_methods]
        
        # 3. Sort by preference (Flash is fastest/cheapest, Pro is smartest)
        # We look for 'flash' first
        for m in generative_models:
            if 'flash' in m.name and '1.5' in m.name:
                return m.name
        
        # Fallback: Any Gemini model
        for m in generative_models:
            if 'gemini' in m.name:
                return m.name
                
        return None
    except Exception as e:
        st.sidebar.error(f"API Connection Error: {e}")
        return None

def analyze_content(content_text, api_key):
    # 1. Auto-Discover Model
    model_name = get_working_model(api_key)
    
    if not model_name:
        st.error("❌ Could not find any active AI models for your API Key. Please generate a new key.")
        return None
    
    # Show user which model we picked
    debug_placeholder.success(f"✅ Connected to: `{model_name}`")
    
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
        st.error(f"❌ Analysis Failed using {model_name}. Error: {e}")
        st.info("Tip: If the error says '429' or 'Quota', wait 1 minute and try again.")
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
