import streamlit as st
import pandas as pd
import requests
import html
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer & Sök", page_icon="☪️", layout="centered")

# --- REGLER FÖR TEXTHANTERING (OPTIMERAD: Definieras globalt) ---
# 1. Regex-byggstenar
TASHKEEL = r'[\u064B-\u065F]*'
SPACES = r'\s*'
YA_VARIANTS = f'[يى]{TASHKEEL}'

# 2. Mönster för specifika fraser
RA_BASE = f'ر{TASHKEEL}ض{TASHKEEL}{YA_VARIANTS}{SPACES}ا{TASHKEEL}ل{TASHKEEL}ل{TASHKEEL}ه{TASHKEEL}{SPACES}ع{TASHKEEL}ن{TASHKEEL}ه{TASHKEEL}'
PATTERN_RA_ANHUMA = f'{RA_BASE}م{TASHKEEL}ا{TASHKEEL}'
PATTERN_RA_ANHA   = f'{RA_BASE}ا{TASHKEEL}'
PATTERN_RA_ANHU   = f'{RA_BASE}'

SALLALLAH = f'ص{TASHKEEL}ل{TASHKEEL}{YA_VARIANTS}{SPACES}ا{TASHKEEL}ل{TASHKEEL}ل{TASHKEEL}ه{TASHKEEL}{SPACES}ع{TASHKEEL}ل{TASHKEEL}ي{TASHKEEL}ه{TASHKEEL}{SPACES}و{TASHKEEL}س{TASHKEEL}ل{TASHKEEL}م{TASHKEEL}'
RASUL_ALLAH = f'ر{TASHKEEL}س{TASHKEEL}و{TASHKEEL}ل{TASHKEEL}{SPACES}ا{TASHKEEL}ل{TASHKEEL}ل{TASHKEEL}ه{TASHKEEL}'

# 3. Mönster för ordkategorier
ORANGE_WORDS = f'ف{TASHKEEL}ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL} |ف{TASHKEEL}ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL}ت{TASHKEEL} |ي{TASHKEEL}ق{TASHKEEL}و{TASHKEEL}ل{TASHKEEL} |ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL}ت{TASHKEEL} |ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL} '
PINK_WORDS = f'ح{TASHKEEL}د{TASHKEEL}ث{TASHKEEL}ن{TASHKEEL}ا|ح{TASHKEEL}د{TASHKEEL}ث{TASHKEEL}ن{TASHKEEL}ي|أ{TASHKEEL}خ{TASHKEEL}ب{TASHKEEL}ر{TASHKEEL}ن{TASHKEEL}ي|أ{TASHKEEL}خ{TASHKEEL}ب{TASHKEEL}ر{TASHKEEL}ن{TASHKEEL}ا|عَن{TASHKEEL} |س{TASHKEEL}م{TASHKEEL}ع{TASHKEEL}ت{TASHKEEL}ُ?'
QUOTE_STR = r'".*?"|«.*?»|“.*?”'

# NYTT: Mönster för måsvingar (hanterar allt inuti {})
CURLY_BRACES = r'\{.*?\}'

# 4. Det stora huvudmönstret (Kompileras en gång för prestanda)
MASTER_PATTERN = re.compile(
    f'(?P<quote>{QUOTE_STR})|(?P<saw>{SALLALLAH})|(?P<ra_anhuma>{PATTERN_RA_ANHUMA})|'
    f'(?P<ra_anha>{PATTERN_RA_ANHA})|(?P<ra_anhu>{PATTERN_RA_ANHU})|'
    f'(?P<pink>{PINK_WORDS})|(?P<orange>{ORANGE_WORDS})|(?P<red>{RASUL_ALLAH})|'
    f'(?P<curly>{CURLY_BRACES})'
)

# 5. Städ-mönster
CLEAN_CHARS_PATTERN = re.compile(r'[^\u0020-\u007E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
CLEAN_TASHKEEL_PATTERN = re.compile(r'[\u064B-\u0652]')
CLEAN_ALIF_PATTERN = re.compile(r'[أإآ]')
CLEAN_YA_PATTERN = re.compile(r'ى')

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

    /* --- SÖKFÄLTS-FIX (Nu helt anpassat för Arabiska) --- */
    .stTextInput input {
        direction: rtl;
        text-align: right;
    }
    
    /* Vi behöver inte tvinga placeholder till LTR längre eftersom texten är arabiska */
    .stTextInput input::placeholder {
        direction: rtl;
        text-align: right; 
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
    
    .curly-highlight { color: #0328fc; font-weight: bold; }
    
    /* Sök-highlighting */
    .search-highlight {
        background-color: #fff59d;
        border-radius: 4px;
        padding: 0 2px;
        box-shadow: 0 0 2px rgba(0,0,0,0.1);
    }
    
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
    text = CLEAN_TASHKEEL_PATTERN.sub('', text)
    text = CLEAN_ALIF_PATTERN.sub('ا', text)
    text = CLEAN_YA_PATTERN.sub('ي', text)
    text = text.replace('ـ', '')
    return text

def highlight_search_terms(text, search_words):
    """
    Lägger till gul highlighting på sökorden eller fraserna.
    """
    if not search_words:
        return text
    
    alif_variants = '[اأإآ]'
    ya_variants = '[يى]'
    tashkeel = r'[\u064B-\u065F]*'

    for word in search_words:
        if not word: continue
        
        pattern_chars = []
        for char in word:
            if char == ' ':
                pattern_chars.append(r'\s+')
            elif char == 'ا':
                pattern_chars.append(f'{alif_variants}{tashkeel}')
            elif char in ['ي', 'ى']:
                pattern_chars.append(f'{ya_variants}{tashkeel}')
            else:
                pattern_chars.append(f'{re.escape(char)}{tashkeel}')
        
        full_pattern = "".join(pattern_chars)
        
        try:
            text = re.sub(
                f'({full_pattern})', 
                r'<span class="search-highlight">\1</span>', 
                text
            )
        except re.error:
            pass 

    return text

def apply_original_formatting(original_text):
    """Implementerar din exakta formateringslogik och städning."""
    text_to_process = str(original_text).replace('\ufffd', '').replace('ـ', '').replace('-', '')
    text_to_process = CLEAN_CHARS_PATTERN.sub('', text_to_process)

    if text_to_process.count('"') % 2 != 0:
        text_to_process += '"'

    def formatter_func(match):
        group_name = match.lastgroup
        match_text = match.group(0)
        
        if group_name == 'saw': return '&nbsp;<span class="saw-symbol">ﷺ</span>'
        if group_name in ['ra_anhuma', 'ra_anha', 'ra_anhu']: return '&nbsp;<span class="ra-symbol">ؓ</span>'
        if group_name == 'quote': return f'<b>{match_text}</b>'
        if group_name == 'pink': return f'<span class="narrator-highlight">{match_text}</span>'
        if group_name == 'orange': return f'<span class="qal-highlight">{match_text}</span>'
        if group_name == 'red': return f'<span class="rasul-highlight">{match_text}</span>'
        if group_name == 'curly': return f'<span class="curly-highlight">{match_text}</span>'
        
        return match_text

    formatted = MASTER_PATTERN.sub(formatter_func, text_to_process)
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
            df_book['search_text'] = df_book['text'].apply(clean_for_search)
            return df_book
        except: return pd.DataFrame()
    
    full_df = pd.concat([load_book("bukhari"), load_book("muslim")], ignore_index=True)
    full_df['hadithnumber'] = full_df['hadithnumber'].astype(str).str.replace('.0', '', regex=False)
    return full_df

with st.spinner("Laddar bibliotek..."):
    df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---

# HÄR ÄR ÄNDRINGEN: Platshållaren är nu på arabiska
query = st.text_input("Sök i Bukhari & Muslim:", placeholder='مثال: انما الاعمال')

# --- SÖK OCH VISA RESULTAT ---
if query:
    query = query.strip()

    # --- LOGIK FÖR SÖKTYP ---
    if query.startswith('"') and query.endswith('"'):
        # 1. EXAKT FRAS-SÖKNING
        raw_phrase = query[1:-1]
        
        if raw_phrase.strip():
            cleaned_phrase = clean_for_search(raw_phrase)
            cleaned_phrase_normalized = ' '.join(cleaned_phrase.split())
            mask = df['search_text'].str.contains(cleaned_phrase_normalized, na=False, regex=False)
            search_words = [cleaned_phrase_normalized]
        else:
            mask = pd.Series([False] * len(df))
            search_words = []
            st.warning("Du angav tomma citattecken.")

    else:
        # 2. VANLIG SÖKNING
        cleaned_query = clean_for_search(query)
        search_words = cleaned_query.split()
        
        if search_words:
            mask = pd.Series([True] * len(df))
            for word in search_words:
                mask = mask & df['search_text'].str.contains(word, na=False)
        else:
            mask = pd.Series([False] * len(df))

    # Hämta resultat
    results = df[mask]

    if not results.empty:
        st.write(f"Hittade {len(results)} träffar:")
        for _, row in results.iterrows():
            formatted_text = apply_original_formatting(row['text'])
            formatted_text_highlighted = highlight_search_terms(formatted_text, search_words)
            
            st.markdown(f"""
            <div class="hadith-card">
                <div class="card-header">
                    <span class="meta-tag">📖 {row['book_name']}</span>
                    <span class="meta-tag"># {row['hadithnumber']}</span>
                </div>
                <div class="arabic-text">{formatted_text_highlighted}</div>
                <details>
                    <summary>Original text</summary>
                    <div class="raw-code-box">{row['text']}</div>
                </details>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Inga hadither hittades som matchar din sökning.")
else:
    st.info("Vänligen skriv in sökord ovan för att söka i Bukhari och Muslim.")
