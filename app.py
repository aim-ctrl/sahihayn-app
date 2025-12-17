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
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
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
        font-size: 26px;
        line-height: 1.8;
        direction: rtl;
        text-align: right;
        color: #000;
        width: 100%;
    }
    
    .arabic-text b { font-weight: 700; color: #2E8B57; }
    .qal-highlight { color: #ff8c00; font-weight: bold; }
    .narrator-highlight { color: #ec407a; font-weight: bold; }
    .rasul-highlight { color: #d32f2f; font-weight: bold; }
    
    .saw-symbol { color: #d32f2f; font-size: 1.2em; }
    .ra-symbol { color: #000000; font-size: 1.1em; font-weight: normal; }

    .card-header {
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #f5f5f5; padding-bottom: 15px; direction: ltr; 
    }
    .meta-tag {
        background-color: #f1f8e9; color: #2e7d32; padding: 6px 14px;
        border-radius: 8px; font-size: 0.9rem; font-weight: 700;
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
        except: return pd.DataFrame()
    return pd.concat([load_book("bukhari"), load_book("muslim")], ignore_index=True)

df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
selected_book = st.radio("Välj bok", ["Bukhari", "Muslim"], horizontal=True, label_visibility="collapsed")
hadith_id = st.number_input("Hadith Nummer", min_value=1, value=1, step=1, label_visibility="collapsed")

# --- VISA KORTET ---
current_num_str = str(hadith_id)
result = df[(df['book_name'] == selected_book) & (df['hadithnumber'].astype(str) == current_num_str)]

if not result.empty:
    row = result.iloc[0]
    safe_text = html.escape(str(row['text']).replace('\n', ''))
    if safe_text.count('&quot;') % 2 != 0: safe_text += '&quot;'

    # --- FORMATTERINGSLOGIK ---
    t = r'[\u064B-\u065F]*' # Tashkeel
    s = r'\s*'             # Flexibelt mellanslag
    y = f'[يى]{t}'        # Flexibel Yaa/Alif Maqsura

    # Mönster för Radi Allahu Anhu/Anha/Anhuma (utan och med tashkeel)
    # Vi matchar ord för ord med flexibilitet emellan
    ra_base = f'ر{t}ض{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ن{t}ه{t}'
    pattern_ra_anhuma = f'{ra_base}م{t}ا{t}'
    pattern_ra_anha   = f'{ra_base}ا{t}'
    pattern_ra_anhu   = f'{ra_base}'

    # SAW och Rasul Allah
    sallallah = f'ص{t}ل{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ل{t}ي{t}ه{t}{s}و{t}س{t}ل{t}م{t}'
    rasul_allah = f'ر{t}س{t}و{t}ل{t}{s}ا{t}ل{t}ل{t}ه{t}'

    # Grupper
    orange_words = f'ف{t}ق{t}ا{t}ل{t} |ف{t}ق{t}ا{t}ل{t}ت{t} |ي{t}ق{t}و{t}ل{t} |ق{t}ا{t}ل{t}ت{t} |ق{t}ا{t}ل{t} '
    pink_words = f'ح{t}د{t}ث{t}ن{t}ا|ح{t}د{t}ث{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ا|عَن{t} |س{t}م{t}ع{t}ت{t}ُ?'
    quote_str = r'&quot;.*?&quot;|«.*?»|“.*?”'
    
    master_pattern = f'(?P<quote>{quote_str})|(?P<saw>{sallallah})|(?P<ra_anhuma>{pattern_ra_anhuma})|(?P<ra_anha>{pattern_ra_anha})|(?P<ra_anhu>{pattern_ra_anhu})|(?P<pink>{pink_words})|(?P<orange>{orange_words})|(?P<red>{rasul_allah})'

    def formatter_func(match):
        group_name = match.lastgroup
        text = match.group(0)
        
        if group_name == 'saw': return '<span class="saw-symbol">ﷺ</span>'
        if group_name in ['ra_anhuma', 'ra_anha', 'ra_anhu']: return '<span class="ra-symbol">ؓ</span>'
        if group_name == 'quote':
            if text.startswith('&quot;'): return f'&quot;<b>{text[6:-6]}</b>&quot;'
            return f'{text[0]}<b>{text[1:-1]}</b>{text[-1]}'
        if group_name == 'pink': return f'<span class="narrator-highlight">{text}</span>'
        if group_name == 'orange': return f'<span class="qal-highlight">{text}</span>'
        if group_name == 'red': return f'<span class="rasul-highlight">{text}</span>'
        return text

    formatted_text = re.sub(master_pattern, formatter_func, safe_text)

    st.markdown(f"""
    <div class="hadith-card">
        <div class="card-header">
            <span class="meta-tag">📖 {row['book_name']}</span>
            <span class="meta-tag"># {row['hadithnumber']}</span>
        </div>
        <div class="arabic-text">{formatted_text}</div>
    </div>
    """, unsafe_allow_html=True)
