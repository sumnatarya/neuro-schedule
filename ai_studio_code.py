import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import PyPDF2
import pandas as pd
import json
import re
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="NeuroLearn AI", page_icon="🧠", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Setup")
    api_key = st.text_input("Google Gemini API Key", type="password")
    st.caption("[Get a free key here](https://aistudio.google.com/app/apikey)")
    st.divider()
    st.info("This app uses 'Gemini 1.5 Flash' to analyze entire lectures and generate spaced repetition schedules.")

# --- HELPER FUNCTIONS ---

def clean_json_text(text):
    """Cleans AI response to ensure valid JSON."""
    text = text.replace("```json", "").replace("```", "")
    # Find the first '{' and last '}'
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
    except Exception as e:
        return None

def get_youtube_transcript(url):
    try:
        video_id = ""
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1]
        
        if not video_id:
            return None, "Invalid YouTube Link"

        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        return formatter.format_transcript(transcript), None
    except Exception as e:
        return None, "Could not retrieve transcript. (Video must have captions enabled)"

def analyze_content(content_text, api_key):
    """
    The Brain: Uses Gemini to analyze cognitive load.
    Includes fallback logic to prevent crashes.
    """
    genai.configure(api_key=api_key)
    
    # List of models to try (Newest to Oldest)
    models = ['gemini-1.5-flash', 'gemini-1.5-flash-001', 'gemini-pro']
    active_model = None
    
    # 1. Select a working model
    for m in models:
        try:
            test = genai.GenerativeModel(m)
            active_model = test
            break
        except:
            continue
            
    if not active_model:
        st.error("Could not connect to Google AI. Please check your API Key.")
        return None

    # 2. The Neuro-Science Prompt
    prompt = f"""
    Act as a Neuro-Education Expert. Analyze the following study material.
    
    Output strictly VALID JSON with this structure:
    {{
        "summary": "Two sentence summary of the content.",
        "difficulty_score": (Integer 1-10, where 10 is extremely complex academic material),
        "estimated_study_time_minutes": (Integer, calculate deep learning time based on 75 words per minute for hard text, 150 wpm for easy),
        "key_concepts": ["List", "Of", "5", "Main", "Concepts"],
        "learning_advice": "One specific technique (e.g. 'Use Analogies' or 'Draw Diagrams') tailored to this content type."
    }}

    CONTENT TO ANALYZE:
    {content_text[:25000]}
    """
    
    try:
        response = active_model.generate_content(prompt)
        clean_response = clean_json_text(response.text)
        return json.loads(clean_response)
    except Exception as e:
        st.error(f"Analysis Error: {e}")
        return None

def generate_schedule(start_date, difficulty):
    # Ebbinghaus Forgetting Curve Intervals
    intervals = [0, 1, 3, 7, 14, 30]
    schedule = []
    
    # Neuro-Strategy Selection
    if difficulty >= 7:
        methods = ["📝 Blurting Method", "🗣️ Feynman Technique", "🧩 Interleaved Practice", "🧪 Practical Application", "🔍 Error Analysis", "🏆 Master Review"]
    else:
        methods = ["🧠 Active Recall", "⚡ Quick Quiz", "🔄 Summary Review", "🔗 Concept Mapping", "🎤 Teach a Friend", "✅ Final Check"]

    for i, days in enumerate(intervals):
        date = start_date + timedelta(days=days)
        schedule.append({
            "Session": i + 1,
            "Date": date.strftime("%Y-%m-%d"),
            "Interval": f"+{days} days",
            "Technique": methods[i],
            "Focus": "Encoding" if i == 0 else "Retrieval"
        })
    
    return pd.DataFrame(schedule)

# --- UI LAYOUT ---
st.title("🧠 NeuroSchedule AI")
st.markdown("### The Scientific Learning Calculator")

if not api_key:
    st.warning("⚠️ Please enter your Google Gemini API Key in the sidebar to start.")
    st.stop()

# Tabs
tab1, tab2, tab3 = st.tabs(["📄 Upload PDF", "📺 YouTube Video", "📝 Paste Text"])

content = None
source_label = ""

with tab1:
    pdf = st.file_uploader("Upload Notes/Book", type="pdf")
    if pdf:
        content = extract_pdf_text(pdf)
        source_label = "PDF Document"

with tab2:
    url = st.text_input("YouTube URL")
    if url:
        with st.spinner("Downloading transcript..."):
            text, err = get_youtube_transcript(url)
            if err:
                st.error(err)
            else:
                content = text
                source_label = "Video Transcript"

with tab3:
    txt = st.text_area("Enter text")
    if txt:
        content = txt
        source_label = "Raw Text"

# Action
if content and st.button("🚀 Analyze & Generate Plan", type="primary"):
    with st.spinner("🤖 AI is measuring semantic density and cognitive load..."):
        data = analyze_content(content, api_key)
        
        if data:
            st.divider()
            
            # Top Metrics
            c1, c2, c3 = st.columns(3)
            c1.metric("Difficulty", f"{data['difficulty_score']}/10")
            c2.metric("Study Time", f"{data['estimated_study_time_minutes']} min")
            c3.metric("Source", source_label)
            
            # Insights
            st.subheader("📌 Summary")
            st.info(data['summary'])
            
            st.subheader("🔑 Key Concepts")
            st.write(", ".join([f"**{c}**" for c in data['key_concepts']]))
            
            st.subheader("💡 Neuro-Advice")
            st.success(data['learning_advice'])
            
            # Schedule
            st.subheader("📅 Spaced Repetition Schedule")
            df = generate_schedule(datetime.now(), data['difficulty_score'])
            st.dataframe(df, use_container_width=True, hide_index=True)
