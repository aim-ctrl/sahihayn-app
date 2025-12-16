import streamlit as st
import pandas as pd
import requests
import html
import re # <--- NYTT: Behövs för att leta efter mönster i texten

# --- KONFIGURATION ---
st.set_page_config(
    page_title="Hadith Design Test", 
    page_icon="🎨", 
    layout="centered"
)

# --- CSS / DESIGN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');

    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        border-left: 6px solid #2E8B57;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    
    .arabic-text {
        font-family: 'Scheherazade New', serif;
        font-size: 34px;
        line-height: 2.2;
        direction: rtl;
        text-align: right;
        color: #1f1f1f;
        margin-top: 15px;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 1px dashed #eee;
    }
    
    .english-text {
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 18px;
        line-height: 1.6;
        color: #333;
        margin-bottom: 12px;
        direction: ltr;
        text-align: left;
    }

    /* Header container inside card */
    .card-header {
        display: flex; 
        justify-content: space-between; 
        align-items: flex-start;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 10px;
    }

    .tags-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }

    /* Grön tag (Bok, Nummer, Narrator) */
    .meta-tag {
        display: inline-flex;
        align-items: center;
        background-color: #f1f8e9;
        color: #2e7d32;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        border: 1px solid #dcedc8;
        letter-spacing: 0.3px;
    }

    /* Orange tag (Grade) */
    .grade-tag {
        display: inline-block;
        background-color: #fff3e0; 
        color: #e65100; 
        border: 1px solid #ffe0b2;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
    }

    @media (prefers-color-scheme: dark) {
        .hadith-card { background-color: #262730; border-color: #444; }
        .arabic-text { color: #f0f0f0; border-bottom-color: #444; }
        .english-text { color: #d0d0d0; }
        .meta-tag { background-color: #1b3320; color: #a5d6a7; border-color: #2e5c35; }
        .grade-tag { background-color: #3e2723; color: #ffcc80; border-color: #4e342e; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATAFUNKTIONER ---

@st.cache_data(show_spinner=True)
def load_data():
    # Samma laddningsfunktion som förut
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

# --- EXTRAHERA NARRATOR FUNKTION ---
def extract_narrator_info(text):
    """
    Letar efter 'Narrated X' eller 'X reported'.
    Returnerar: (Namnet på personen, städad text utan namnet)
    """
    narrator = None
    clean_text = text

    # Fall 1: "Narrated Abu Huraira:"
    # Regex förklaring: ^Narrated = Börjar med Narrated. \s+ = mellanslag. (.+?) = Fånga namnet. [:\.] = slutar på : eller .
    match_narrated = re.search(r'^Narrated\s+(.+?)(?::|\.)', text)
    
    # Fall 2: "Abu Huraira reported:"
    match_reported = re.search(r'^(.+?)\s+reported[:\s]', text)

    if match_narrated:
        narrator = match_narrated.group(1)
        # Ta bort "Narrated X:" från texten för att undvika upprepning
        clean_text = re.sub(r'^Narrated\s+.+?[:\.]\s*', '', text)
        
    elif match_reported:
        narrator = match_reported.group(1)
        # Ta bort "X reported:" från texten
        clean_text = re.sub(r'^.+?\s+reported[:\s]*', '', text)

    return narrator, clean_text

# --- UI LAYOUT ---

st.title("🎨 Design Mode")
st.info("Nu testar vi att extrahera 'Narrator' till en egen tag.")

if not df.empty:
    sample_df = df.sample(10)

    for i, row in sample_df.iterrows():
        
        # 1. LOGIK: Hitta narrator och städa texten
        raw_english = str(row['text'])
        narrator_name, cleaned_english_text = extract_narrator_info(raw_english)
        
        # HTML Escape på texten (men använd den städade versionen)
        arabic_safe = html.escape(str(row['arabic_text'])).replace('\n', ' ')
        english_safe = html.escape(cleaned_english_text).replace('\n', '<br>')
        
        # Bygg Narrator Badge (Om vi hittade ett namn)
        narrator_badge = ""
        if narrator_name:
            # Om namnet är väldigt långt (över 25 tecken), korta ner det lite med "..."
            if len(narrator_name) > 25:
                narrator_name = narrator_name[:25] + "..."
            narrator_badge = f"<span class='meta-tag'>👤 {narrator_name}</span>"

        # Bygg Grade Badge
        grade_badge = ""
        if isinstance(row['grades'], list) and len(row['grades']) > 0:
            try:
                g = row['grades'][0]['grade']
                grade_badge = f"<span class='grade-tag'>{g}</span>"
            except:
                pass

        # 2. BYGG HTML
        card_html = f"""
<div class="hadith-card">
    <div class="card-header">
        <div class="tags-container">
            <span class="meta-tag">📖 {row['source_book']}</span>
            <span class="meta-tag"># {row['hadithnumber']}</span>
            {narrator_badge}
        </div>
        {grade_badge}
    </div>
    <div class="arabic-text">{arabic_safe}</div>
    <div class="english-text">{english_safe}</div>
</div>
"""
        st.markdown(card_html, unsafe_allow_html=True)
else:
    st.error("Ingen data.")
