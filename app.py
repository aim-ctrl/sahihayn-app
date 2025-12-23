import streamlit as st
import pandas as pd
import requests
import html
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer & Sök", page_icon="☪️", layout="centered")

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
    
    .saw-symbol { 
        color: #d32f2f; 
        font-family: 'Scheherazade New', serif; 
        font-size: 1.1em;
        margin-right: 4px; 
    }

    .ra-symbol { 
        color: #000000; 
        font-family: 'Scheherazade New', serif; 
        font-weight: normal; 
        font-size: 1.1em;
        margin-right: 4px; 
    }

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
        background-color: #262730; 
        color: #ffffff;            
        border: 1px solid #444;
        padding: 15px;
        border-radius: 8px;
        font-family: 'Scheherazade New', serif;
        white-space: pre-wrap; 
        direction: rtl;
        text-align: right;
        font-size: 18px;
        margin-top: 10px;
    }
    
    summary { color: #000; font-weight: bold; cursor: pointer; }
</style>
""", unsafe_allow_html=True)

# --- HJÄLPFUNKTIONER ---
def clean_for_search(text):
    """Normaliserar arabiska tecken för att sökningen ska fungera oavsett diakritik."""
    if not isinstance(text, str): return ""
    # Ta bort diakritiker (tashkeel)
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # Normalisera Alif (أ , إ , آ -> ا)
    text = re.sub(r'[أإآ]', 'ا', text)
    # Normalisera Ya/Alif Maqsura (ى -> ي)
    text = re.sub(r'ى', 'ي', text)
    # Ta bort Tatweel (ـ)
    text = text.replace('ـ', '')
    return text

def apply_original_formatting(original_text):
    """Implementerar din exakta formateringslogik och städning."""
    # 1. Städning och fix för citattecken
    text_to_process = str(original_text).replace('\ufffd', '').replace('ـ', '').replace('-', '')
    text_to_process = re.sub(r'[^\u0020-\u007E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', text_to_process)

    # Kontrollera om citattecken är ojämna (t.ex. Bukhari #1)
    if text_to_process.count('"') % 2 != 0:
        text_to_process += '"'

    # 2. Formatteringslogik (Regex)
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
        match_text = match.group(0)
        
        if group_name == 'saw': return '&nbsp;<span class="saw-symbol">ﷺ</span>'
        if group_name in ['ra_anhuma', 'ra_anha', 'ra_anhu']: return '&nbsp;<span class="ra-symbol">ؓ</span>'
        if group_name == 'quote': return f'<b>{match_text}</b>'
        if group_name == 'pink': return f'<span class="narrator-highlight">{match_text}</span>'
        if group_name == 'orange': return f'<span class="qal-highlight">{match_text}</span>'
        if group_name == 'red': return f'<span class="rasul-highlight">{match_text}</span>'
        return match_text

    formatted = re.sub(master_pattern, formatter_func, text_to_process)
    
    # Sista putsning
    formatted = re.sub(r'\s+', ' ', formatted)
    formatted = re.sub(r'\s+([\.،,])', r'\1', formatted)
    return formatted.strip()

# --- DATALOGIK ---
@st.cache_data(show_spinner=False)
def get_dataset():
    def load_book(book_name):
        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        try:
            resp = requests.get(url).json()
            df_book = pd.DataFrame(resp['hadiths'])
            df_book['book_name'] = book_name.capitalize()
            # Skapa sök-index utan diakritiker vid laddning för prestanda
            df_book['search_text'] = df_book['text'].apply(clean_for_search)
            return df_book
        except: return pd.DataFrame()
    
    full_df = pd.concat([load_book("bukhari"), load_book("muslim")], ignore_index=True)
    full_df['hadithnumber'] = full_df['hadithnumber'].astype(str).str.replace('.0', '', regex=False)
    return full_df

with st.spinner("Laddar bibliotek..."):
    df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
st.write("## Hadith Sökmotor")
query = st.text_input("Sök i Bukhari & Muslim (arabiska ord separerade med mellanslag):", placeholder="t.ex. انما الاعمال")

# --- SÖK OCH VISA RESULTAT ---
if query:
    # Förbered sökorden genom att normalisera dem också
    cleaned_query = clean_for_search(query)
    search_words = cleaned_query.split()
    
    # Skapa en mask för "OCH"-sökning
    mask = pd.Series([True] * len(df))
    for word in search_words:
        mask = mask & df['search_text'].str.contains(word, na=False)
    
    results = df[mask]

    if not results.empty:
        st.write(f"Hittade {len(results)} träffar:")
        for _, row in results.iterrows():
            # Tillämpa din ursprungliga formatering på varje träff
            formatted_text = apply_original_formatting(row['text'])
            
            # Rendera kortet exakt enligt din design
            st.markdown(f"""
            <div class="hadith-card">
                <div class="card-header">
                    <span class="meta-tag">📖 {row['book_name']}</span>
                    <span class="meta-tag"># {row['hadithnumber']}</span>
                </div>
                <div class="arabic-text">{formatted_text}</div>
                <details>
                    <summary>Original text</summary>
                    <div class="raw-code-box">{row['text']}</div>
                </details>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Inga hadither hittades som innehåller alla dessa ord.")
else:
    st.info("Vänligen skriv in sökord ovan för att söka i Bukhari och Muslim.")
