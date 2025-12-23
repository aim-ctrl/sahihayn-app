import streamlit as st
import pandas as pd
import requests
import re

# --- KONFIGURATION & CSS (Behåll din exakta design) ---
st.set_page_config(page_title="Hadith Viewer", page_icon="☪️", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');
    .hadith-card {
        background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px;
        padding: 24px; margin-bottom: 20px; border-right: 6px solid #2E8B57;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); display: flex; flex-direction: column;
    }
    .arabic-text {
        font-family: 'Scheherazade New', serif; font-size: 28px; line-height: 1.8;
        direction: rtl; text-align: right; color: #1a1a1a; margin-top: 20px; width: 100%;
    }
    .arabic-text b { font-weight: 700; color: #2E8B57; }
    .qal-highlight { color: #ff8c00; font-weight: bold; }
    .narrator-highlight { color: #ec407a; font-weight: bold; }
    .rasul-highlight { color: #d32f2f; font-weight: bold; }
    .saw-symbol { color: #d32f2f; font-size: 1.1em; }
    .ra-symbol { color: #000000; font-size: 1.1em; }
    .card-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f5f5f5; padding-bottom: 15px; }
    .meta-tag { background-color: #f1f8e9; color: #2e7d32; padding: 6px 14px; border-radius: 8px; font-size: 0.9rem; font-weight: 700; border: 1px solid #dcedc8; }
    .raw-code-box { background-color: #262730; color: #ffffff; padding: 15px; border-radius: 8px; font-family: 'Scheherazade New', serif; white-space: pre-wrap; direction: rtl; text-align: right; font-size: 18px; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- HJÄLPFUNKTIONER ---
def clean_for_search(text):
    """Rensar texten maximalt för att garantera sökmatchning."""
    if not isinstance(text, str): return ""
    # 1. Ta bort alla diakritiker
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # 2. Normalisera varianter av Alif, Ya och Hamza som ofta ställer till det
    text = re.sub(r'[أإآ]', 'ا', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ـ', '', text) # Tatweel
    return text

def format_hadith_logic(original_text):
    """Din exakta formateringsmotor för visning."""
    cleaned = str(original_text).replace('\ufffd', '').replace('ـ', '').replace('-', '').replace('\n', ' ')
    cleaned = re.sub(r'[^\u0020-\u007E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', cleaned)
    
    t, s, y = r'[\u064B-\u065F]*', r'\s*', f'[يى][\u064B-\u065F]*'
    ra_base = f'ر{t}ض{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ن{t}ه{t}'
    
    master_pattern = (
        f'(?P<quote>".*?"|«.*?»|“.*?”)|(?P<saw>ص{t}ل{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ل{t}ي{t}ه{t}{s}و{t}س{t}ل{t}م{t})|'
        f'(?P<ra>{ra_base}(م{t}ا{t}|ا{t})?)|(?P<pink>ح{t}د{t}ث{t}ن{t}ا|ح{t}د{t}ث{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ا|عَن{t} |س{t}م{t}ع{t}ت{t}ُ?)|'
        f'(?P<orange>ف{t}ق{t}ا{t}ل{t}ت? |ي{t}ق{t}و{t}ل{t} |ق{t}ا{t}ل{t}ت? )|(?P<red>ر{t}س{t}و{t}ل{t}{s}ا{t}ل{t}ل{t}ه{t})'
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
            # Här skapar vi den dolda sök-texten
            df['search_clean'] = df['text'].apply(clean_for_search)
            return df
        except: return pd.DataFrame()
    
    return pd.concat([load_book("bukhari"), load_book("muslim")], ignore_index=True)

df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
selected_book = st.radio("Välj bok", ["Bukhari", "Muslim"], horizontal=True)

# Två sökmetoder
search_query = st.text_input("Sök i text (flera ord = OCH)", placeholder="t.ex. انما الاعمال")
hadith_id_input = st.number_input("Eller sök på nummer", min_value=0, value=0)

# --- SÖKLOGIK ---
results = pd.DataFrame()

if search_query:
    # 1. Filtrera på bok
    book_df = df[df['book_name'] == selected_book]
    # 2. Rensa söksträngen på samma sätt som databasen
    clean_query = clean_for_search(search_query)
    words = clean_query.split()
    
    mask = pd.Series([True] * len(book_df))
    for word in words:
        mask = mask & book_df['search_clean'].str.contains(word, na=False)
    results = book_df[mask]
elif hadith_id_input > 0:
    results = df[(df['book_name'] == selected_book) & (df['hadithnumber'] == str(hadith_id_input))]

# --- RENDERING ---
if not results.empty:
    st.write(f"Visar {len(results)} träffar i {selected_book}:")
    for _, row in results.iterrows():
        formatted_text = format_hadith_logic(row['text'])
        st.markdown(f"""
        <div class="hadith-card">
            <div class="card-header">
                <span class="meta-tag">📖 {row['book_name']}</span>
                <span class="meta-tag"># {row['hadithnumber']}</span>
            </div>
            <div class="arabic-text">{formatted_text}</div>
            <details><summary>Original</summary><div class="raw-code-box">{row['text']}</div></details>
        </div>
        """, unsafe_allow_html=True)
elif search_query:
    st.warning("Inga träffar i den valda boken. Kontrollera stavning eller byt bok.")
