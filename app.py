import streamlit as st
import pandas as pd
import requests
import html
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer", page_icon="☪️", layout="centered")

# --- CSS / DESIGN (Exakt din originaldesign) ---
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
        margin-bottom: 25px;
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
        color: #1a1a1a;
        margin-top: 20px;
        width: 100%;
    }
    
    .arabic-text b { font-weight: 700; color: #2E8B57; }
    .qal-highlight { color: #ff8c00; font-weight: bold; }
    .narrator-highlight { color: #ec407a; font-weight: bold; }
    .rasul-highlight { color: #d32f2f; font-weight: bold; }
    
    .saw-symbol { color: #d32f2f; font-family: 'Scheherazade New', serif; font-size: 1.1em; margin-right: 4px; }
    .ra-symbol { color: #000000; font-family: 'Scheherazade New', serif; font-weight: normal; font-size: 1.1em; margin-right: 4px; }

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
        background-color: #262730; color: #ffffff; border: 1px solid #444;
        padding: 15px; border-radius: 8px; font-family: 'Scheherazade New', serif;
        white-space: pre-wrap; direction: rtl; text-align: right; font-size: 18px; margin-top: 10px;
    }
    summary { color: #000; font-weight: bold; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# --- HJÄLPFUNKTIONER ---
def clean_for_search(text):
    """Normaliserar arabiska för sökning utan att påverka visningen."""
    if not isinstance(text, str): return ""
    text = re.sub(r'[\u064B-\u0652]', '', text) # Diakritiker
    text = re.sub(r'[أإآ]', 'ا', text) # Normalisera Alif
    text = re.sub(r'ى', 'ي', text) # Normalisera Ya
    text = text.replace('ـ', '') # Tatweel
    return text

def apply_original_formatting(original_text):
    """Din exakta formateringslogik från ursprungskoden."""
    # 1. NY STÄDNINGSPROCESS (Från din kod)
    cleaned_text = str(original_text).replace('\ufffd', '').replace('ـ', '').replace('-', '')
    cleaned_text = re.sub(r'[^\u0020-\u007E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', cleaned_text)

    # 2. FORMATTERINGSLOGIK (Regex-definitioner)
    t = r'[\u064B-\u065F]*' 
    s = r'\s*'             
    y = f'[يى]{t}'        

    ra_base = f'ر{t}ض{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ن{t}ه{t}'
    pattern_ra_anhuma = f'{ra_base}م{t}ا{t}'
    pattern_ra_anha   = f'{ra_base}ا{t}'
    pattern_ra_anhu   = f'{ra_base}'

    sallallah = f'ص{t}ل{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ل{t}ي{t}ه{t}{s}و{t}س{t}ل{t}م{t}'
    rasul_allah = f'ر{t}س{t}و{t}ل{t}{s}ا{t}ل{t}ل{t}ه{t}'

    orange_words = f'ف{t}ق{t}ا{t}ل{t} |ف{t}ق{t}ا{t}ل{t}ت{t} |ي{t}ق{t}و{t}ل{t} |ق{t}ا{t}ل{t}ت{t} |ق{t}ا{t}ل{t} '
    pink_words = f'ح{t}د{t}ث{t}ن{t}ا|ح{t}د{t}ث{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ا|عَن{t} |س{t}م{t}ع{t}ت{t}ُ?'
    quote_str = r'".*?"|«.*?»|“.*?”'
    
    master_pattern = f'(?P<quote>{quote_str})|(?P<saw>{sallallah})|(?P<ra_anhuma>{pattern_ra_anhuma})|(?P<ra_anha>{pattern_ra_anha})|(?P<ra_anhu>{pattern_ra_anhu})|(?P<pink>{pink_words})|(?P<orange>{orange_words})|(?P<red>{rasul_allah})'

    def formatter_func(match):
        group_name = match.lastgroup
        text = match.group(0)
        
        if group_name == 'saw': return '&nbsp;<span class="saw-symbol">ﷺ</span>'
        if group_name in ['ra_anhuma', 'ra_anha', 'ra_anhu']: return '&nbsp;<span class="ra-symbol">ؓ</span>'
        if group_name == 'quote': return f'<b>{text}</b>'
        if group_name == 'pink': return f'<span class="narrator-highlight">{text}</span>'
        if group_name == 'orange': return f'<span class="qal-highlight">{text}</span>'
        if group_name == 'red': return f'<span class="rasul-highlight">{text}</span>'
        return text

    formatted_text = re.sub(master_pattern, formatter_func, cleaned_text)

    # 3. SISTA STÄDNING (Inklusive hantering av mellanrum vid skiljetecken)
    formatted_text = re.sub(r'\s+', ' ', formatted_text)
    formatted_text = re.sub(r'\s+([\.،,])', r'\1', formatted_text)
    return formatted_text.strip()

# --- DATALOGIK ---
@st.cache_data(show_spinner=False)
def get_dataset():
    def load_book(book_name):
        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        try:
            resp = requests.get(url).json()
            df = pd.DataFrame(resp['hadiths'])
            df['book_name'] = book_name.capitalize()
            # Vi skapar sök-indexet vid laddning
            df['search_clean'] = df['text'].apply(clean_for_search)
            return df
        except: return pd.DataFrame()
    
    df_b = load_book("bukhari")
    df_m = load_book("muslim")
    return pd.concat([df_b, df_m], ignore_index=True)

with st.spinner("Laddar bibliotek..."):
    df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
st.title("Hadith Sök")
search_query = st.text_input("Sök i Bukhari & Muslim (t.ex. انما الاعمال):", placeholder="Skriv här...")

# --- SÖK OCH RENDERING ---
if search_query:
    clean_query = clean_for_search(search_query)
    words = clean_query.split()
    
    # "OCH"-logik för alla ord
    mask = pd.Series([True] * len(df))
    for word in words:
        mask = mask & df['search_clean'].str.contains(word, na=False)
    
    results = df[mask]

    if not results.empty:
        st.write(f"Hittade {len(results)} träffar:")
        for _, row in results.iterrows():
            # Kör din exakta formatering
            display_text = apply_original_formatting(row['text'])
            
            # Rendera kortet exakt som i din originalkod
            st.markdown(f"""
            <div class="hadith-card">
                <div class="card-header">
                    <span class="meta-tag">📖 {row['book_name']}</span>
                    <span class="meta-tag"># {row['hadithnumber']}</span>
                </div>
                <div class="arabic-text">{display_text}</div>
                <details>
                    <summary>Original text</summary>
                    <div class="raw-code-box">{row['text']}</div>
                </details>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Inga träffar hittades.")
else:
    st.write("Vänligen skriv in sökord för att se resultat.")
