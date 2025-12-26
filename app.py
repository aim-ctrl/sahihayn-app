import streamlit as st
import pandas as pd
import requests
import html
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer & Sök", page_icon="☪️", layout="centered")

# --- INITIALISERA SESSION STATE ---
if 'active_book_filter' not in st.session_state:
    st.session_state.active_book_filter = None
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""

# --- REGLER FÖR TEXTHANTERING ---
TASHKEEL = r'[\u064B-\u065F]*'
SPACES = r'\s*'
YA_VARIANTS = f'[يى]{TASHKEEL}'

RA_BASE = f'ر{TASHKEEL}ض{TASHKEEL}{YA_VARIANTS}{SPACES}ا{TASHKEEL}ل{TASHKEEL}ل{TASHKEEL}ه{TASHKEEL}{SPACES}ع{TASHKEEL}ن{TASHKEEL}ه{TASHKEEL}'
PATTERN_RA_ANHUMA = f'{RA_BASE}م{TASHKEEL}ا{TASHKEEL}'
PATTERN_RA_ANHA   = f'{RA_BASE}ا{TASHKEEL}'
PATTERN_RA_ANHU   = f'{RA_BASE}'

SALLALLAH = f'ص{TASHKEEL}ل{TASHKEEL}{YA_VARIANTS}{SPACES}ا{TASHKEEL}ل{TASHKEEL}ل{TASHKEEL}ه{TASHKEEL}{SPACES}ع{TASHKEEL}ل{TASHKEEL}ي{TASHKEEL}ه{TASHKEEL}{SPACES}و{TASHKEEL}س{TASHKEEL}ل{TASHKEEL}م{TASHKEEL}'
RASUL_ALLAH = f'ر{TASHKEEL}س{TASHKEEL}و{TASHKEEL}ل{TASHKEEL}{SPACES}ا{TASHKEEL}ل{TASHKEEL}ل{TASHKEEL}ه{TASHKEEL}'

ORANGE_WORDS = f'ف{TASHKEEL}ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL} |ف{TASHKEEL}ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL}ت{TASHKEEL} |ي{TASHKEEL}ق{TASHKEEL}و{TASHKEEL}ل{TASHKEEL} |ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL}ت{TASHKEEL} |ق{TASHKEEL}ا{TASHKEEL}ل{TASHKEEL} '
PINK_WORDS = f'ح{TASHKEEL}د{TASHKEEL}ث{TASHKEEL}ن{TASHKEEL}ا|ح{TASHKEEL}د{TASHKEEL}ث{TASHKEEL}ن{TASHKEEL}ي|أ{TASHKEEL}خ{TASHKEEL}ب{TASHKEEL}ر{TASHKEEL}ن{TASHKEEL}ي|أ{TASHKEEL}خ{TASHKEEL}ب{TASHKEEL}ر{TASHKEEL}ن{TASHKEEL}ا|عَن{TASHKEEL} |س{TASHKEEL}م{TASHKEEL}ع{TASHKEEL}ت{TASHKEEL}ُ?'
QUOTE_STR = r'".*?"|«.*?»|“.*?”'
CURLY_BRACES = r'\{.*?\}'

MASTER_PATTERN = re.compile(
    f'(?P<quote>{QUOTE_STR})|(?P<saw>{SALLALLAH})|(?P<ra_anhuma>{PATTERN_RA_ANHUMA})|'
    f'(?P<ra_anha>{PATTERN_RA_ANHA})|(?P<ra_anhu>{PATTERN_RA_ANHU})|'
    f'(?P<pink>{PINK_WORDS})|(?P<orange>{ORANGE_WORDS})|(?P<red>{RASUL_ALLAH})|'
    f'(?P<curly>{CURLY_BRACES})'
)

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

    /* --- SÖKFÄLTS-FIXAR --- */
    .stTextInput input {
        direction: rtl;
        text-align: right;
    }
    .stTextInput input::placeholder {
        direction: rtl;
        text-align: right; 
    }
    [data-testid="InputInstructions"] { display: none !important; }

    /* --- KOMPAKTA KNAPPAR (JUSTERAD) --- */
    
    /* 1. Tvinga minskat avstånd (gap) mellan elementen inuti kolumnen */
    [data-testid="column"] > div {
        gap: -0.5rem !important; /* Här styr du avståndet mellan knapparna vertikalt */
    }

    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        font-size: 8px;          
        padding: 2px 4px;        
        min-height: 0px;          
        height: auto;             
        line-height: 1;
        margin-top: 0px !important;
        margin-bottom: 0px !important;
    }
    
    /* Justera containern runt knappen för säkerhets skull */
    div.stButton {
        margin-bottom: 0px; 
    }
    
    [data-testid="column"] {
        padding: 0px 0px;
    }

    /* --- HADITH KORT DESIGN --- */
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
        font-size: 18px;
        line-height: 1.7;
        direction: rtl;
        text-align: right;
        color: #1a1a1a;
        margin-top: 0px;
        width: 100%;
    }
    
    .arabic-text b { font-weight: 700; color: #2E8B57; }
    .qal-highlight { color: #ff8c00; font-weight: bold; }
    .narrator-highlight { color: #ec407a; font-weight: bold; }
    .rasul-highlight { color: #d32f2f; font-weight: bold; }
    .curly-highlight { color: #0328fc; font-weight: bold; }
    
    .search-highlight {
        background-color: #fff59d;
        border-radius: 4px;
        padding: 0 2px;
        box-shadow: 0 0 2px rgba(0,0,0,0.1);
    }
    
    .saw-symbol, .ra-symbol { 
        font-family: 'Scheherazade New', serif; 
        font-size: 0.9em;
        margin-right: 4px; 
    }
    .saw-symbol { color: #d32f2f; }
    .ra-symbol { color: #000000; font-weight: normal; }

    .card-header {
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #f5f5f5; padding-bottom: 15px; direction: ltr; 
    }
    .meta-tag {
        background-color: #f1f8e9; color: #2e7d32; padding: 6px 14px;
        border-radius: 8px; font-size: 0.75rem; font-weight: 700;
        border: 1px solid #dcedc8;
        white-space: nowrap; 
    }

    .raw-code-box {
        background-color: #262730; color: #ffffff; border: 1px solid #444;
        padding: 15px; border-radius: 8px; font-family: 'Scheherazade New', serif;
        white-space: pre-wrap; direction: rtl; text-align: right;
        font-size: 14px; margin-top: 10px;
    }
    
    summary { color: #000; font-weight: bold; cursor: pointer; font-size: 12px }
</style>
""", unsafe_allow_html=True)

# --- HJÄLPFUNKTIONER ---
def clean_for_search(text):
    if not isinstance(text, str): return ""
    text = CLEAN_TASHKEEL_PATTERN.sub('', text)
    text = CLEAN_ALIF_PATTERN.sub('ا', text)
    text = CLEAN_YA_PATTERN.sub('ي', text)
    text = text.replace('ـ', '')
    return text

def highlight_search_terms(text, search_words):
    if not search_words: return text
    alif_variants = '[اأإآ]'
    ya_variants = '[يى]'
    tashkeel = r'[\u064B-\u065F]*'

    for word in search_words:
        if not word: continue
        pattern_chars = []
        for char in word:
            if char == ' ': pattern_chars.append(r'\s+')
            elif char == 'ا': pattern_chars.append(f'{alif_variants}{tashkeel}')
            elif char in ['ي', 'ى']: pattern_chars.append(f'{ya_variants}{tashkeel}')
            else: pattern_chars.append(f'{re.escape(char)}{tashkeel}')
        
        full_pattern = "".join(pattern_chars)
        try:
            text = re.sub(f'({full_pattern})', r'<span class="search-highlight">\1</span>', text)
        except re.error: pass 
    return text

def apply_original_formatting(original_text):
    text_to_process = str(original_text).replace('\ufffd', '').replace('ـ', '').replace('-', '')
    text_to_process = CLEAN_CHARS_PATTERN.sub('', text_to_process)
    if text_to_process.count('"') % 2 != 0: text_to_process += '"'

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
    books_config = [
        ("bukhari", "Sahih Bukhari"), ("muslim", "Sahih Muslim"),
        ("abudawud", "Sunan Abu Dawood"), ("tirmidhi", "Jami' At-Tirmidhi"),
        ("nasai", "Sunan An-Nasa'i"), ("ibnmajah", "Sunan Ibn Majah")
    ]
    dataframes = []
    def load_book(api_slug, display_name):
        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{api_slug}.json"
        try:
            resp = requests.get(url).json()
            if 'hadiths' in resp:
                df_book = pd.DataFrame(resp['hadiths'])
                df_book['book_name'] = display_name
                df_book['search_text'] = df_book['text'].apply(clean_for_search)
                return df_book
        except Exception: pass 
        return pd.DataFrame()
    
    for slug, name in books_config:
        dataframes.append(load_book(slug, name))
    
    full_df = pd.concat(dataframes, ignore_index=True)
    if not full_df.empty:
        full_df['hadithnumber'] = full_df['hadithnumber'].astype(str).str.replace('.0', '', regex=False)
    return full_df

with st.spinner("Laddar bibliotek (Al-Kutub Al-Sittah)..."):
    df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
query = st.text_input("Sök i Al-Kutub Al-Sittah (De sex böckerna):", placeholder='مثال: انما الاعمال')

if query:
    query = query.strip()
    if query != st.session_state.last_query:
        st.session_state.active_book_filter = None
        st.session_state.last_query = query

    if query.startswith('"') and query.endswith('"'):
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
        cleaned_query = clean_for_search(query)
        search_words = cleaned_query.split()
        if search_words:
            mask = pd.Series([True] * len(df))
            for word in search_words:
                mask = mask & df['search_text'].str.contains(word, na=False)
        else:
            mask = pd.Series([False] * len(df))

    all_results = df[mask]

    if not all_results.empty:
        total_hits = len(all_results)
        book_counts = all_results['book_name'].value_counts()
        
        # --- KOMPAKTA FILTER-KNAPPAR ---
        st.markdown(f'<div style="margin-bottom: 5px; direction: ltr; font-size: 11px;"><strong>Hittade {total_hits} träffar. Filtrera:</strong></div>', unsafe_allow_html=True)
        
        # Skapa EXAKT TVÅ kolumner med litet gap
        cols = st.columns(2, gap="small")
        
        # Loopa igenom böcker och placera dem varannan gång i vänster/höger kolumn
        for idx, (book_name, count) in enumerate(book_counts.items()):
            is_active = (st.session_state.active_book_filter == book_name)
            btn_type = "primary" if is_active else "secondary"
            label = f"{book_name} ({count})"
            
            # idx % 2 ger 0 för första, 1 för andra, 0 för tredje... (Växelvis placering)
            with cols[idx % 2]:
                if st.button(label, key=f"btn_{book_name}", type=btn_type):
                    if is_active:
                        st.session_state.active_book_filter = None
                    else:
                        st.session_state.active_book_filter = book_name
                    st.rerun()


        # --- VISA RESULTAT ---
        results_to_display = all_results
        if st.session_state.active_book_filter:
            results_to_display = all_results[all_results['book_name'] == st.session_state.active_book_filter]
        
        for _, row in results_to_display.iterrows():
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
    st.info("Vänligen skriv in sökord ovan för att söka i Al-Kutub Al-Sittah.")
