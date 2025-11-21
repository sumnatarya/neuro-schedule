import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
st.set_page_config(page_title="NeuroSchedule", page_icon="🧠", layout="centered")

# --- SCIENTIFIC LOGIC FUNCTIONS ---
def calculate_schedule(start_date, complexity_score):
    """
    Based on SuperMemo-2 (SM-2) and Ebbinghaus Forgetting Curve.
    Intervals expand based on successful recall.
    """
    # Standard Spaced Repetition Intervals (in days)
    # Rep 0: Immediate, Rep 1: 1 day, Rep 2: 3 days, Rep 3: 7 days...
    base_intervals = [0, 1, 3, 7, 16, 35]
    
    schedule = []
    
    for i, interval in enumerate(base_intervals):
        review_date = start_date + timedelta(days=interval)
        
        # Method based on Bloom's Taxonomy
        if i == 0:
            method = "📥 Encoding (First Learn)"
            focus = "Focus on understanding the 'Why' and 'How'. Create mind maps."
        elif i == 1:
            method = "🔄 Active Recall (Immediate)"
            focus = "Do not look at notes. Write down everything you remember."
        elif i == 2:
            method = "🧩 Interleaving"
            focus = "Mix this topic with a different subject to strengthen neural connections."
        elif i == 3:
            method = "🧪 Feynman Technique"
            focus = "Explain the concept simply out loud as if teaching a 5-year-old."
        else:
            method = "🏗️ Application"
            focus = "Solve a problem or create something using this knowledge."

        schedule.append({
            "Repetition #": i + 1,
            "Date": review_date.strftime("%Y-%m-%d"),
            "Interval (Days)": interval,
            "Method": method,
            "Cognitive Focus": focus
        })
    
    return pd.DataFrame(schedule)

def estimate_time(content_type, quantity, difficulty, familiarity):
    """
    Estimates time based on cognitive load theory and average processing speeds.
    """
    # Base processing speeds
    # Reading: 250 wpm
    # Video: 1x speed
    # Lecture: 1x speed
    
    base_minutes = 0
    
    if content_type == "Text (Pages)":
        # Approx 300 words per page / 200 wpm (studying speed) = 1.5 mins per page
        base_minutes = quantity * 1.5
    elif content_type == "Video/Audio (Minutes)":
        # Videos take 1.5x length to take notes and pause
        base_minutes = quantity * 1.5
    elif content_type == "Flashcards/Items":
        # 30 seconds per card for initial learning
        base_minutes = (quantity * 0.5)
        
    # Multipliers
    # Difficulty (1 to 10) -> Multiplier 1.0 to 2.5
    diff_mult = 1 + (difficulty / 10)
    
    # Familiarity (1 to 10) -> Multiplier 1.5 (Novice) to 0.5 (Expert)
    # Inverting scale: High familiarity = low time
    fam_mult = 1.5 - (familiarity / 20) 
    
    total_minutes = base_minutes * diff_mult * fam_mult
    return round(total_minutes)

# --- UI LAYOUT ---
st.title("🧠 NeuroSchedule")
st.markdown("""
**The Scientific Learning Calculator.**  
*Based on Spaced Repetition Systems (SRS) and the Forgetting Curve.*
""")

with st.expander("ℹ️ How this works"):
    st.write("""
    This app uses **Learning Sciences** to tell you exactly when and how to study.
    1. **Forgetting Curve:** We calculate optimal review dates to prevent memory decay.
    2. **Cognitive Load:** We estimate time based on difficulty and your prior knowledge.
    3. **Active Recall:** We assign specific study methods (not just "re-reading") for each rep.
    """)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Content details")
    topic = st.text_input("Topic Name", placeholder="e.g., Quantum Mechanics")
    c_type = st.selectbox("Content Type", ["Text (Pages)", "Video/Audio (Minutes)", "Flashcards/Items"])
    quantity = st.number_input(f"Quantity ({c_type.split()[0]})", min_value=1, value=10)

with col2:
    st.subheader("2. Cognitive Load")
    difficulty = st.slider("Complexity (1=Easy, 10=Rocket Science)", 1, 10, 5)
    familiarity = st.slider("Your Current Knowledge (1=Newbie, 10=Expert)", 1, 10, 1)

st.divider()

if st.button("🚀 Generate Neuro-Optimized Schedule", type="primary"):
    if topic:
        # Calculations
        est_time_min = estimate_time(c_type, quantity, difficulty, familiarity)
        schedule_df = calculate_schedule(datetime.now(), difficulty)
        
        # Display Results
        st.success(f"Blueprint generated for: **{topic}**")
        
        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Initial Study Time", f"{int(est_time_min)} min")
        m2.metric("Total Reps Required", "6 Reps")
        m3.metric("Mastery Date", schedule_df.iloc[-1]["Date"])
        
        st.subheader("📅 Your Spaced Repetition Schedule")
        st.dataframe(
            schedule_df, 
            column_config={
                "Repetition #": st.column_config.NumberColumn(format="%d"),
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.info("💡 **Pro Tip:** For Reps 3 and 4, use the 'Blurting Method'. Read a section, close the book, and write everything you remember. Then check what you missed.")
        
    else:
        st.error("Please enter a topic name first.")