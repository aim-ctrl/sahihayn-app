import streamlit as st
import pandas as pd
import requests
import html
import re

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
        border-right: 6px solid #2E8B57; /* Ändrade till höger kant för RTL-känsla */
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

    /* Header container */
    .card-header {
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        border-bottom: 1px solid #f0f0f0;
        padding-bottom: 10px;
        margin-bottom: 10px;
        direction: ltr; /* Behåll header LTR så tagsen ligger snyggt */
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

# --- DATA LOADING ---

@st.cache_data(show_spinner=True)
def load_data():
    def fetch_book_pair(book_name):
        url_eng = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-{book_name}.json"
        url_ara = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        try:
            resp_eng = requests.get(url_eng).json()
            resp_ara = requests.get(url_ara).json()
            df_eng = pd.DataFrame(resp_eng['hadiths'])
            df_ara = pd.DataFrame(resp_ara['hadiths'])
            ara_map = dict(zip(df_ara['hadithnumber'], df_ara['text']))
            df_eng['arabic_text'] = df_eng['hadithnumber'].map(ara_map)
            df_eng['source_book'] = book_name.capitalize()
            return df_eng.dropna(subset=['text', 'arabic_text'])
        except:
            return pd.DataFrame()

    df_bukhari = fetch_book_pair("bukhari")
    df_muslim = fetch_book_pair("muslim")
    return pd.concat([df_bukhari, df_muslim], ignore_index=True)

try:
    with st.spinner('Laddar data...'):
        df = load_data()
except:
    df = pd.DataFrame()

# --- HELPER FUNCTIONS ---

def extract_narrator_name(text):
    """Endast för att hitta namnet till taggen, texten visas inte."""
    match_narrated = re.search(r'^Narrated\s+(.+?)(?::|\.)', text)
    match_reported = re.search(r'^(.+?)\s+reported[:\s]', text)
    
    if match_narrated:
        return match_narrated.group(1)
    elif match_reported:
        return match_reported.group(1)
    return None

# --- UI LAYOUT ---

st.title("📖 Hadith Reader")

if not df.empty:
    # Hämta 10 slumpmässiga
    sample_df = df.sample(10)

    for i, row in sample_df.iterrows():
        
        # 1. Hämta data
        arabic_safe = html.escape(str(row['arabic_text'])).replace('\n', ' ')
        
        # Vi använder engelska texten BARA för att hitta namnet på berättaren
        narrator_name = extract_narrator_name(str(row['text']))
        
        # Skapa Badge HTML
        narrator_badge = ""
        if narrator_name:
            if len(narrator_name) > 20: narrator_name = narrator_name[:20] + "..."
            narrator_badge = f"<span class='meta-tag'>👤 {narrator_name}</span>"

        grade_badge = ""
        if isinstance(row['grades'], list) and len(row['grades']) > 0:
            try:
                g = row['grades'][0]['grade']
                grade_badge = f"<span class='grade-tag'>{g}</span>"
            except: pass

        # 2. BYGG HTML - Extremt kompakt för att undvika formatteringsfel
        # OBS: Inga onödiga mellanslag eller indrag i f-stringen
        card_html = f"""<div class="hadith-card"><div class="card-header"><div class="tags-left"><span class="meta-tag">📖 {row['source_book']}</span><span class="meta-tag"># {row['hadithnumber']}</span>{narrator_badge}</div>{grade_badge}</div><div class="arabic-text">{arabic_safe}</div></div>"""

        st.markdown(card_html, unsafe_allow_html=True)

else:
    st.error("Kunde inte ladda data.")
