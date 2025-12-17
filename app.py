import streamlit as st
import pandas as pd
import requests
import html
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer", page_icon="☪️", layout="centered")

# --- CSS / DESIGN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');
    
    #MainMenu { visibility: hidden !important; }
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; display: none !important; }
    
    a[href*="streamlit.io/cloud"] { display: none !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }
    [class*="viewerBadge"] { display: none !important; }

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }

    div[data-testid="stNumberInput"] input {
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        color: #2E8B57;
    }

    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 24px;
        margin-top: 20px;
        border-right: 6px solid #2E8B57;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
    }
    
    .arabic-text {
        font-family: 'Scheherazade New', serif;
        font-size: 24px;
        line-height: 1.8;
        direction: rtl;
        text-align: right;
        color: #000;
        margin-top: 20px;
        margin-bottom: 20px;
        width: 100%;
    }
    
    .arabic-text b {
        font-weight: 700;
        color: #2E8B57; /* Grön färg på citaten */
    }

    /* ORANGE FÄRG: !important tvingar fram färgen även inuti <b> taggar */
    .qal-highlight {
        color: #ff8c00 !important; 
        font-weight: bold;
    }

    .card-header {
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        border-bottom: 1px solid #f5f5f5;
        padding-bottom: 15px;
        direction: ltr; 
    }

    .meta-tag {
        background-color: #f1f8e9;
        color: #2e7d32;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 700;
        border: 1px solid #dcedc8;
    }

    details {
        margin-top: 10px;
        border-top: 1px dashed #ddd;
        padding-top: 10px;
        font-size: 0.8rem;
        color: #666;
    }
    summary {
        cursor: pointer;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .raw-code-box {
        background-color: #f8f9fa;
        border: 1px solid #eee;
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
        white-space: pre-wrap; 
        direction: rtr;
        text-align: right;
        color: #000;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATALOGIK ---

@st.cache_data(show_spinner=False)
def get_dataset():
    def load_book(book_name):
        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        try:
            resp = requests.get(url).json()
            df = pd.DataFrame(resp['hadiths'])
            df['book_name'] = book_name.capitalize()
            return df
        except:
            return pd.DataFrame()

    df_bukhari = load_book("bukhari")
    df_muslim = load_book("muslim")
    full_df = pd.concat([df_bukhari, df_muslim], ignore_index=True)
    full_df['hadithnumber'] = full_df['hadithnumber'].astype(str).str.replace('.0', '', regex=False)
    return full_df

with st.spinner("Laddar bibliotek..."):
    df = get_dataset()
    
# --- ANVÄNDARGRÄNSSNITT ---

selected_book = st.radio(
    "Välj bok",
    ["Bukhari", "Muslim"], 
    horizontal=True,
    label_visibility="collapsed"
)

hadith_id = st.number_input(
    "Hadith Nummer", 
    min_value=1, 
    value=1, 
    step=1,
    format="%d" ,
    label_visibility="collapsed"
)

# --- VISA KORTET ---

current_num_str = str(hadith_id)

result = df[
    (df['book_name'] == selected_book) & 
    (df['hadithnumber'] == current_num_str)
]

if not result.empty:
    row = result.iloc[0]
    
    raw_api_text = str(row['text'])
    display_text = raw_api_text.replace('\n', '')
    safe_text = html.escape(display_text)
    
    if safe_text.count('&quot;') % 2 != 0:
        safe_text += '&quot;'

    # --- STEG 1: FÄRGLÄGG SPECIFIKA ORD (QAL m.fl.) ---
    # Vi gör detta FÖRST så att span-taggarna hamnar inuti citaten sen.
    
    # Tashkeel (vokaler) regex
    t = r'[\u064B-\u065F]*' 

    # Bygg ord
    yaqul = f'ي{t}ق{t}و{t}ل{t}'
    qalat = f'ق{t}ا{t}ل{t}ت{t}'
    qal = f'ق{t}ا{t}ل{t}'

    full_pattern = f'({yaqul}|{qalat}|{qal})'

    formatted_text = re.sub(full_pattern, r'<span class="qal-highlight">\1</span>', safe_text)

    # --- STEG 2: FÄRGLÄGG CITAT (FETSTIL & GRÖN) ---
    # Detta görs SIST, vilket betyder att hela citatet omsluts av <b>.
    # Om ordet "Qal" finns inuti, kommer HTML att se ut så här: <b>... <span class="qal">Qal</span> ...</b>
    
    formatted_text = re.sub(r'&quot;(.*?)&quot;', r'&quot;<b>\1</b>&quot;', formatted_text)
    formatted_text = re.sub(r'«(.*?)»', r'«<b>\1</b>»', formatted_text)
    formatted_text = re.sub(r'“([^”]*?)”', r'“<b>\1</b>”', formatted_text)

    # --- RENDERA KORTET ---
    
    card_html = f"""
<div class="hadith-card">
    <div class="card-header">
        <span class="meta-tag">📖 {row['book_name']}</span>
        <span class="meta-tag"># {row['hadithnumber']}</span>
    </div>
    <div class="arabic-text">{formatted_text}</div>
    <details>
        <summary>Original</summary>
        <div class="raw-code-box">{html.escape(raw_api_text)}</div>
    </details>
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    st.write("")
else:
    st.info(f"Nummer **{current_num_str}** finns inte i **{selected_book}**. (Vissa nummer kan saknas eller ha suffix som 'a').")
