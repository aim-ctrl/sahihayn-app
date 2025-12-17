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
        font-size: 28px;
        line-height: 1.8;
        direction: rtl;
        text-align: right;
        color: #000;
        margin-top: 20px;
        width: 100%;
    }
    
    .arabic-text b { font-weight: 700; color: #2E8B57; }
    .qal-highlight { color: #ff8c00; font-weight: bold; }
    .narrator-highlight { color: #ec407a; font-weight: bold; }
    .rasul-highlight { color: #d32f2f; font-weight: bold; }
    
    .saw-symbol { color: #d32f2f; font-family: 'Scheherazade New', serif; font-size: 1.2em; }
    .ra-symbol { color: #000000; font-family: 'Scheherazade New', serif; font-weight: normal; font-size: 1.1em; }

    .card-header {
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #f5f5f5; padding-bottom: 15px; direction: ltr; 
    }
    .meta-tag {
        background-color: #f1f8e9; color: #2e7d32; padding: 6px 14px;
        border-radius: 8px; font-size: 0.9rem; font-weight: 700;
        border: 1px solid #dcedc8;
    }
    .raw-code-box {
        background-color: #f8f9fa; border: 1px solid #eee; padding: 10px;
        border-radius: 5px; font-family: monospace; white-space: pre-wrap; 
        direction: rtl; text-align: right; font-size: 12px; margin-top: 10px;
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
    
    df_bukhari = load_book("bukhari")
    df_muslim = load_book("muslim")
    full_df = pd.concat([df_bukhari, df_muslim], ignore_index=True)
    full_df['hadithnumber'] = full_df['hadithnumber'].astype(str).str.replace('.0', '', regex=False)
    return full_df

with st.spinner("Laddar bibliotek..."):
    df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
selected_book = st.radio("Välj bok", ["Bukhari", "Muslim"], horizontal=True, label_visibility="collapsed")
hadith_id = st.number_input("Hadith Nummer", min_value=1, value=1, step=1, format="%d", label_visibility="collapsed")

# --- VISA KORTET ---
current_num_str = str(hadith_id)
result = df[(df['book_name'] == selected_book) & (df['hadithnumber'] == current_num_str)]

if not result.empty:
    row = result.iloc[0]
    raw_api_text = str(row['text'])
    safe_text = html.escape(raw_api_text.replace('\n', ''))
    
    if safe_text.count('&quot;') % 2 != 0: safe_text += '&quot;'

    # --- FORMATTERINGSLOGIK ---
    # t_all inkluderar nu även Tatweel (ـ) och bindestreck (-) tillsammans med vokaler
    t_all = r'[\u064B-\u065F\u0640-]*' 
    s = r'\s*'             
    y = f'[يى]{t_all}'        

    # Mönster för Radi Allahu Anhu/Anha/Anhuma
    ra_base = f'{t_all}ر{t_all}ض{t_all}{y}{s}ا{t_all}ل{t_all}ل{t_all}ه{t_all}{s}ع{t_all}ن{t_all}ه{t_all}'
    pattern_ra_anhuma = f'{ra_base}م{t_all}ا{t_all}'
    pattern_ra_anha   = f'{ra_base}ا{t_all}'
    pattern_ra_anhu   = f'{ra_base}'

    sallallah = f'ص{t_all}ل{t_all}{y}{s}ا{t_all}ل{t_all}ل{t_all}ه{t_all}{s}ع{t_all}ل{t_all}ي{t_all}ه{t_all}{s}و{t_all}س{t_all}ل{t_all}م{t_all}'
    rasul_allah = f'ر{t_all}س{t_all}و{t_all}ل{t_all}{s}ا{t_all}ل{t_all}ل{t_all}ه{t_all}'

    orange_words = f'ف{t_all}ق{t_all}ا{t_all}ل{t_all} |ف{t_all}ق{t_all}ا{t_all}ل{t_all}ت{t_all} |ي{t_all}ق{t_all}و{t_all}ل{t_all} |ق{t_all}ا{t_all}ت{t_all} |ق{t_all}ا{t_all}ل{t_all} '
    pink_words = f'ح{t_all}د{t_all}ث{t_all}ن{t_all}ا|ح{t_all}د{t_all}ث{t_all}ن{t_all}ي|أ{t_all}خ{t_all}ب{t_all}ر{t_all}ن{t_all}ي|أ{t_all}خ{t_all}ب{t_all}ر{t_all}ن{t_all}ا|عَن{t_all} |س{t_all}م{t_all}ع{t_all}ت{t_all}ُ?'
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

    # --- RENDERING ---
    st.markdown(f"""
    <div class="hadith-card">
        <div class="card-header">
            <span class="meta-tag">📖 {row['book_name']}</span>
            <span class="meta-tag"># {row['hadithnumber']}</span>
        </div>
        <div class="arabic-text">{formatted_text}</div>
        <details>
            <summary style="font-size:12px; color:#999; margin-top:20px; cursor:pointer;">Visa originaltext</summary>
            <div class="raw-code-box">{html.escape(raw_api_text)}</div>
        </details>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info(f"Hittade ingen hadith med nummer {hadith_id} i {selected_book}.")
