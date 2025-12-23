import streamlit as st
import pandas as pd
import requests
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Sök", page_icon="☪️", layout="centered")

# --- CSS / DESIGN (Din exakta originaldesign) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');
    
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
    
    .saw-symbol { color: #d32f2f; font-family: 'Scheherazade New', serif; font-size: 1.1em; }
    .ra-symbol { color: #000000; font-family: 'Scheherazade New', serif; font-size: 1.1em; }

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
        background-color: #262730; color: #ffffff; padding: 15px;
        border-radius: 8px; font-family: 'Scheherazade New', serif;
        white-space: pre-wrap; direction: rtl; text-align: right; font-size: 18px;
    }
    summary { color: #888; cursor: pointer; margin-top: 10px; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# --- HJÄLPFUNKTIONER ---
def clean_for_search(text):
    """Normaliserar arabiska för robust sökning."""
    if not isinstance(text, str): return ""
    # Ta bort diakritiker
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # Normalisera Alif och Ya (för att hantera stavningsvarianter)
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ى', 'ي', text)
    text = text.replace('ـ', '') # Ta bort Tatweel
    return text

def format_hadith_logic(original_text):
    """Din formateringsmotor med färger och symboler."""
    cleaned = str(original_text).replace('\ufffd', '').replace('ـ', '').replace('-', '').replace('\n', ' ')
    cleaned = re.sub(r'[^\u0020-\u007E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', cleaned)
    
    t, s, y = r'[\u064B-\u065F]*', r'\s*', f'[يى][\u064B-\u065F]*'
    ra_base = f'ر{t}ض{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ن{t}ه{t}'
    
    master_pattern = (
        f'(?P<quote>".*?"|«.*?»|“.*?”)|'
        f'(?P<saw>ص{t}ل{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ل{t}ي{t}ه{t}{s}و{t}س{t}ل{t}م{t})|'
        f'(?P<ra>{ra_base}(م{t}ا{t}|ا{t})?)|'
        f'(?P<pink>ح{t}د{t}ث{t}ن{t}ا|ح{t}د{t}ث{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ا|عَن{t} |س{t}م{t}ع{t}ت{t}ُ?)|'
        f'(?P<orange>ف{t}ق{t}ا{t}ل{t}ت? |ي{t}ق{t}و{t}ل{t} |ق{t}ا{t}ل{t}ت? )|'
        f'(?P<red>ر{t}س{t}و{t}ل{t}{s}ا{t}ل{t}ل{t}ه{t})'
    )

    def repl(m):
        g = m.lastgroup
        txt = m.group(0)
        if g == 'saw': return '&nbsp;<span class="saw-symbol">ﷺ</span>'
        if g == 'ra': return '&nbsp;<span class="ra-symbol">ؓ</span>'
        if g == 'quote': return f'<b>{txt}</b>'
        if g == 'pink': return f'<span class="narrator-highlight">{txt}</span>'
        if g == 'orange': return f'<span class="qal-highlight">{txt}</span>'
        if g == 'red': return f'<span class="rasul-highlight">{txt}</span>'
        return txt

    return re.sub(master_pattern, repl, cleaned).strip()

# --- DATALOGIK ---
@st.cache_data(show_spinner=False)
def get_dataset():
    def load_book(book_name):
        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        try:
            resp = requests.get(url).json()
            df = pd.DataFrame(resp['hadiths'])
            df['book_name'] = book_name.capitalize()
            df['search_clean'] = df['text'].apply(clean_for_search)
            return df
        except: return pd.DataFrame()
    
    return pd.concat([load_book("bukhari"), load_book("muslim")], ignore_index=True)

df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
st.title("Hadith Global Sök")
query = st.text_input("Sök i både Bukhari & Muslim:", placeholder="Skriv arabiska ord här...")

# --- SÖKPROCESS ---
if query:
    # Tvätta användarens input på samma sätt som datan
    clean_query = clean_for_search(query)
    words = clean_query.split()
    
    # Skapa en mask som kräver ALLA ord (AND-logik)
    mask = pd.Series([True] * len(df))
    for word in words:
        mask = mask & df['search_clean'].str.contains(word, na=False)
    
    results = df[mask]

    if not results.empty:
        st.write(f"Hittade {len(results)} matchningar:")
        for _, row in results.iterrows():
            formatted_text = format_hadith_logic(row['text'])
            st.markdown(f"""
            <div class="hadith-card">
                <div class="card-header">
                    <span class="meta-tag">📖 {row['book_name']}</span>
                    <span class="meta-tag"># {row['hadithnumber']}</span>
                </div>
                <div class="arabic-text">{formatted_text}</div>
                <details>
                    <summary>Originaltext</summary>
                    <div class="raw-code-box">{row['text']}</div>
                </details>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Inga resultat hittades för denna kombination av ord.")
else:
    st.info("Skriv in ord i fältet ovan för att börja söka.")
