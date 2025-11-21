import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import PyPDF2
import pandas as pd
import json
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="NeuroLearn AI", page_icon="🧠", layout="wide")

# --- SIDEBAR: API KEY ---
with st.sidebar:
    st.title("⚙️ Settings")
    api_key = st.text_input("Enter Google Gemini API Key", type="password")
    st.caption("Get a free key at: [aistudio.google.com](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    st.write("### Supported Formats")
    st.write("📄 **PDF Documents** (Lecture notes, chapters)")
    st.write("📺 **YouTube Videos** (Lectures, Tutorials)")
    st.write("📝 **Raw Text** (Paste content)")

# --- LOGIC FUNCTIONS ---

def extract_pdf_text(uploaded_file):
    try:
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return None

def get_youtube_transcript(url):
    try:
        # Extract Video ID
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1]
        else:
            return None, "Invalid YouTube URL"

        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        formatter = TextFormatter()
        text_formatted = formatter.format_transcript(transcript)
        return text_formatted, None
    except Exception as e:
        return None, str(e)

def analyze_with_gemini(content_text, api_key):
    genai.configure(api_key=api_key)
    
    # Use Flash model for speed and long context
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # The Scientific Prompt
    prompt = f"""
    You are an expert Learning Scientist and Neuro-educator. 
    Analyze the following content provided below.
    
    Your goal is to create a study plan based on Cognitive Load Theory and the Forgetting Curve.
    
    Return ONLY valid JSON with this exact structure (no markdown formatting):
    {{
        "summary": "A concise 2-sentence summary of what this content is about.",
        "difficulty_score": (Integer 1-10, where 10 is PhD level Physics, 1 is a Bedtime Story),
        "estimated_study_time_minutes": (Integer, calculated time to deeply LEARN this, not just read. Assume 100 wpm processing speed for hard concepts),
        "key_concepts": ["Concept 1", "Concept 2", "Concept 3", "Concept 4", "Concept 5"],
        "learning_advice": "Specific advice on how to tackle this specific topic based on its structure."
    }}

    CONTENT TO ANALYZE:
    {content_text[:20000]} 
    """
    # Note: Limiting char count to 20k for safety, though Gemini handles more.
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "")
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"AI Analysis Failed: {e}")
        return None

def generate_schedule(start_date, difficulty):
    # Spaced Repetition Logic
    # Intervals expand based on SM-2 algorithm logic
    intervals = [0, 1, 3, 7, 14, 30]
    
    schedule = []
    
    methods_easy = ["Review Summary", "Active Recall", "Practice Quiz", "Relate to other topics"]
    methods_hard = ["Feynman Technique", "Blurting Method", "Interleaved Practice", "Detailed Mind Map"]
    
    method_list = methods_hard if difficulty > 6 else methods_easy
    
    for i, interval in enumerate(intervals):
        date = start_date + timedelta(days=interval)
        
        # Cycle through methods if we run out
        method = method_list[i % len(method_list)]
        
        if i == 0:
            focus = "📥 Encoding: Break down and understand."
        elif i == 1:
            focus = "🧠 Retrieval: Force memory without notes."
        else:
            focus = "🏗️ Application: Use the knowledge."

        schedule.append({
            "Review Session": i + 1,
            "Date": date.strftime("%Y-%m-%d"),
            "Interval": f"+{interval} days",
            "Method": method,
            "Focus": focus
        })
        
    return pd.DataFrame(schedule)

# --- MAIN UI ---
st.title("🧠 NeuroLearn AI")
st.markdown("""
**The AI-Powered Learning Strategist.**  
Upload your content. The AI analyzes the *semantic density* to calculate exactly how long and when you should study.
""")

if not api_key:
    st.warning("⚠️ Please enter your Google Gemini API Key in the sidebar to activate the AI brain.")
    st.stop()

# TABS FOR INPUT
tab1, tab2, tab3 = st.tabs(["📄 PDF Upload", "📺 YouTube Video", "📝 Paste Text"])

content_text = None
source_type = None

with tab1:
    pdf_file = st.file_uploader("Upload Lecture Notes / Book Chapter", type=["pdf"])
    if pdf_file:
        content_text = extract_pdf_text(pdf_file)
        source_type = "PDF Document"

with tab2:
    yt_url = st.text_input("Paste YouTube URL (Lectures/Tutorials)")
    if yt_url:
        with st.spinner("Fetching Transcript..."):
            content_text, error = get_youtube_transcript(yt_url)
            if error:
                st.error(f"Could not get video: {error}. (Video must have captions)")
            else:
                source_type = "Video Transcript"

with tab3:
    raw_text = st.text_area("Paste raw text here")
    if raw_text:
        content_text = raw_text
        source_type = "Raw Text"

# --- EXECUTION ---
if content_text and st.button("🚀 Generate Neuro-Optimized Plan", type="primary"):
    with st.spinner("🤖 AI is analyzing cognitive load and concepts..."):
        
        # 1. AI Analysis
        analysis = analyze_with_gemini(content_text, api_key)
        
        if analysis:
            st.divider()
            st.success("Analysis Complete!")
            
            # 2. Metrics Display
            col1, col2, col3 = st.columns(3)
            col1.metric("Difficulty Score", f"{analysis['difficulty_score']}/10")
            col2.metric("Est. Deep Work Time", f"{analysis['estimated_study_time_minutes']} min")
            col3.metric("Source", source_type)
            
            st.subheader("📝 AI Summary")
            st.info(analysis['summary'])
            
            st.subheader("💡 Key Concepts to Master")
            # Display key concepts as "Flashcard" style tags
            st.markdown(" ".join([f"`{c}`" for c in analysis['key_concepts']]))
            
            st.subheader("👨‍🏫 Learning Advice")
            st.write(analysis['learning_advice'])
            
            # 3. Schedule Generation
            st.subheader("📅 Spaced Repetition Calendar")
            schedule_df = generate_schedule(datetime.now(), analysis['difficulty_score'])
            
            st.dataframe(
                schedule_df, 
                column_config={
                    "Review Session": st.column_config.NumberColumn(format="%d"),
                },
                use_container_width=True,
                hide_index=True
            )
            
            st.caption("This schedule is based on the Ebbinghaus Forgetting Curve to maximize retention.")
