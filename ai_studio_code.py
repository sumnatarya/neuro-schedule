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

# --- SESSION STATE INITIALIZATION ---
if "valid_model" not in st.session_state:
    st.session_state.valid_model = None

# --- SIDEBAR & IMMEDIATE DIAGNOSTICS ---
with st.sidebar:
    st.header("🔑 Setup")
    api_key_input = st.text_input("Google Gemini API Key", type="password")
    
    # Clean the key
    api_key = api_key_input.strip() if api_key_input else None
    
    st.divider()
    st.write("### 🛠️ Connection Status")
    
    # IMMEDIATE CHECK LOGIC
    if api_key:
        try:
            genai.configure(api_key=api_key)
            # Try to list models to verify connection
            all_models = list(genai.list_models())
            
            # Find the best model
            found_model = None
            for m in all_models:
                if 'generateContent' in m.supported_generation_methods:
                    if 'flash' in m.name and '1.5' in m.name:
                        found_model = m.name
                        break
            
            if not found_model:
                # Fallback
                found_model = "gemini-pro"

            st.session_state.valid_model = found_model
            st.success(f"✅ **Connected!**\n\nUsing: `{found_model}`")
            
        except Exception as e:
            st.session_state.valid_model = None
            st.error(f"❌ **Connection Failed**\n\nError: {str(e)}")
            st.info("Check if your API Key is correct or create a new one.")
    else:
        st.warning("Waiting for Key...")

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

def analyze_content(content_text, model_name):
    # Use the model we found in the sidebar check
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
        st.error(f"Analysis Error: {e}")
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

# --- MAIN UI ---
st.title("🧠 NeuroSchedule AI")

# Stop user if key is invalid
if not st.session_state.valid_model:
    st.info("👈 Please enter a valid API Key in the sidebar to start.")
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
    with st.spinner("Running Neuro-Analysis..."):
        # Pass the valid model from session state
        data = analyze_content(content, st.session_state.valid_model)
        
        if data:
            st.divider()
            c1, c2 = st.columns(2)
            c1.metric("Difficulty", f"{data['difficulty_score']}/10")
            c2.metric("Study Time", f"{data['estimated_study_time_minutes']} min")
            
            st.info(f"**Summary:** {data['summary']}")
            st.write("**Key Concepts:** " + ", ".join(data['key_concepts']))
            st.success(f"💡 **Strategy:** {data['learning_advice']}")
            
            st.subheader("📅 Your Schedule")
            st.dataframe(generate_schedule(datetime.now(), data['difficulty_score']), use_container_width=True, hide_index=True)
