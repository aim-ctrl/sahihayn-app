import streamlit as st
import pandas as pd
import html

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Hadith Reader", 
    page_icon="☪️", 
    layout="centered"
)

# --- CSS / STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');

    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 24px;
        border-right: 6px solid #2E8B57;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
    }
    
    .arabic-text {
        font-family: 'Scheherazade New', serif;
        font-size: 36px;
        line-height: 2.3;
        direction: rtl;
        text-align: right;
        color: #000;
        margin-top: 15px;
        width: 100%;
    }

    .card-header {
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        border-bottom: 1px solid #f0f0f0;
        padding-bottom: 10px;
        margin-bottom: 10px;
        direction: ltr; 
    }

    .tags-left {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }

    .meta-tag {
        background-color: #f1f8e9;
        color: #2e7d32;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid #dcedc8;
    }

    .grade-tag {
        background-color: #fff3e0; 
        color: #e65100; 
        border: 1px solid #ffe0b2;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    @media (prefers-color-scheme: dark) {
        .hadith-card { background-color: #1e1e1e; border-color: #333; }
        .arabic-text { color: #ffffff; }
        .meta-tag { background-color: #1b3320; color: #a5d6a7; border-color: #2e5c35; }
        .card-header { border-bottom-color: #333; }
        .grade-tag { background-color: #3e2723; color: #ffcc80; border-color: #4e342e; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATA LOADING (FRÅN DIN CSV) ---

@st.cache_data
def load_data():
    try:
        # Läser filen hadith_db.csv som måste finnas i samma mapp/repo
        df = pd.read_csv("hadith_db.csv")
        
        # Säkerställ att text är strängar (om någon cell är tom i Excel)
        df['narrator'] = df['narrator'].fillna("")
        df['grade_text'] = df['grade_text'].fillna("")
        df['arabic_text'] = df['arabic_text'].fillna("")
        
        return df
    except FileNotFoundError:
        return None

# Ladda data
df = load_data()

# --- UI LAYOUT ---

st.title("📖 Hadith Reader")

if df is not None and not df.empty:
    
    # Visa 10 slumpmässiga (eller byt till sökning senare)
    sample_df = df.sample(10)

    for i, row in sample_df.iterrows():
        
        # Hämta data direkt från dina CSV-kolumner
        arabic_text = html.escape(str(row['arabic_text'])).replace('\n', ' ')
        book = row['source_book']
        number = row['hadithnumber']
        narrator = str(row['narrator']).strip()
        grade = str(row['grade_text']).strip()

        # Skapa tags
        narrator_badge = ""
        if narrator:
            # Korta ner om namnet är jättelångt
            if len(narrator) > 25: narrator = narrator[:25] + "..."
            narrator_badge = f"<span class='meta-tag'>👤 {narrator}</span>"

        grade_badge = ""
        if grade:
             grade_badge = f"<span class='grade-tag'>{grade}</span>"

        # Bygg kortet
        card_html = f"""<div class="hadith-card"><div class="card-header"><div class="tags-left"><span class="meta-tag">📖 {book}</span><span class="meta-tag"># {number}</span>{narrator_badge}</div>{grade_badge}</div><div class="arabic-text">{arabic_text}</div></div>"""

        st.markdown(card_html, unsafe_allow_html=True)

elif df is None:
    st.error("Hittade inte filen 'hadith_db.csv'. Se till att du har skapat den och laddat upp den till GitHub.")
else:
    st.error("Filen verkar vara tom.")
