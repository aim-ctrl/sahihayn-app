import streamlit as st
import pandas as pd
import requests
import html

# --- KONFIGURATION ---
st.set_page_config(
    page_title="Hadith Design Test", 
    page_icon="🎨", 
    layout="centered"
)

# --- CSS / DESIGN ---
st.markdown("""
<style>
    /* 1. IMPORTERA FONTEN FRÅN GOOGLE */
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');

    /* Card Design */
    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 16px; /* Lite rundare hörn */
        padding: 24px;
        margin-bottom: 24px;
        border-left: 6px solid #2E8B57; /* SeaGreen */
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        /* Fix för layout-problem */
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    
    .arabic-text {
        font-family: 'Scheherazade New', serif;
        font-size: 34px; /* Lite större för tydlighet */
        line-height: 2.2;
        direction: rtl;
        text-align: right;
        color: #1f1f1f;
        margin-top: 10px;
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

    /* Meta Data Tags (Bok och nummer) */
    .meta-tag {
        display: inline-block;
        background-color: #f1f8e9;
        color: #2e7d32;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        margin-right: 8px;
        border: 1px solid #dcedc8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Grade Tag (Sahih etc) */
    .grade-tag {
        display: inline-block;
        background-color: #fff3e0; 
        color: #e65100; 
        border: 1px solid #ffe0b2;
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
    }

    /* Mörkt läge */
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
    """Hämtar Bukhari och Muslim (Eng + Ara) och slår ihop dem."""
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
            
        except Exception as e:
            return pd.DataFrame()

    df_bukhari = fetch_book_pair("bukhari")
    df_muslim = fetch_book_pair("muslim")
    return pd.concat([df_bukhari, df_muslim], ignore_index=True)

# Ladda data
try:
    with st.spinner('Laddar data för design-test...'):
        df = load_data()
except:
    df = pd.DataFrame()

# --- UI LAYOUT ---

st.title("🎨 Design Mode")
st.info("Visar 10 slumpmässiga hadither för att kontrollera layout och font.")

# Hämta 10 slumpmässiga rader för att testa designen
if not df.empty:
    sample_df = df.sample(10)

    for i, row in sample_df.iterrows():
        
        # 1. STÄDA TEXTEN
        arabic_safe = html.escape(str(row['arabic_text'])).replace('\n', ' ')
        english_safe = html.escape(str(row['text'])).replace('\n', '<br>')
        
        # Hantera Grade snyggt
        grade_badge = ""
        if isinstance(row['grades'], list) and len(row['grades']) > 0:
            try:
                g = row['grades'][0]['grade']
                grade_badge = f"<span class='grade-tag'>{g}</span>"
            except:
                pass

        # 2. BYGG HTML (Utan indragning för att undvika kod-block-felet)
        card_html = f"""
<div class="hadith-card">
<div style="display:flex; justify-content:space-between; align-items:center;">
    <div>
        <span class="meta-tag">📖 {row['source_book']}</span>
        <span class="meta-tag"># {row['hadithnumber']}</span>
    </div>
    {grade_badge}
</div>
<div class="arabic-text">{arabic_safe}</div>
<div class="english-text">{english_safe}</div>
</div>
"""
        # 3. RENDERA
        st.markdown(card_html, unsafe_allow_html=True)

else:
    st.error("Ingen data kunde laddas.")
