import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import PyPDF2
import pandas as pd
import json
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="NeuroLearn AI", page_icon="🧠", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Setup")
    api_key = st.text_input("Google Gemini API Key", type="password")
    st.caption("Get a key: [aistudio.google.com](https://aistudio.google.com/app/apikey)")

# --- ROBUST AI FUNCTIONS ---

def get_available_model(api_key):
    """
    Dynamically finds a working model so the app never crashes.
    """
    genai.configure(api_key=api_key)
    try:
        # Ask Google what models are available to this API Key
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Priority List: Try to find Flash, then Pro, then any Gemini
        for model_name in available_models:
            if "flash" in model_name and "1.5" in model_name:
                return model_name
        
        for model_name in available_models:
            if "pro" in model_name and "1.5" in model_name:
                return model_name
                
        for model_name in available_models:
            if "gemini" in model_name:
                return model_name
                
        return "gemini-pro" # Final Fallback
    except Exception as e:
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
    except Exception as e:
        return None, "Video must have captions enabled."

def analyze_content(content_text, api_key):
    # 1. Find the best model dynamically
    model_name = get_available_model(api_key)
    if not model_name:
        st.error("Could not list models. Check API Key.")
        return None
        
    model = genai.GenerativeModel(model_name)
    
    # 2. Prompt
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
        st.error(f"AI Error using model {model_name}: {e}")
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
    with st.spinner("Connecting to Google AI..."):
        data = analyze_content(content, api_key)
        if data:
            c1, c2 = st.columns(2)
            c1.metric("Difficulty", f"{data['difficulty_score']}/10")
            c2.metric("Time", f"{data['estimated_study_time_minutes']} min")
            st.info(data['summary'])
            st.write("**Concepts:** " + ", ".join(data['key_concepts']))
            st.success(f"💡 **Tip:** {data['learning_advice']}")
            st.dataframe(generate_schedule(datetime.now(), data['difficulty_score']), use_container_width=True, hide_index=True)
