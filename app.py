import streamlit as st
import pandas as pd
import requests
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer", page_icon="☪️", layout="centered")

# (Behåll din befintliga CSS här, jag hoppar över den för att spara plats)
# ... [DIN CSS KOD] ...

# --- HJÄLPFUNKTIONER FÖR ARABISKA ---
def remove_diacritics(text):
    """Tar bort arabiska diakritiker (tashkeel) för sökändamål."""
    if not isinstance(text, str):
        return ""
    # Regex för arabiska diakritiker: fatha, damma, kasra, sukun, shadda, tanween
    diacritics_pattern = re.compile(r'[\u064B-\u0652]')
    text = re.sub(diacritics_pattern, '', text)
    # Valfritt: Normalisera Alif (valfritt beroende på hur strikt sökningen ska vara)
    # text = re.sub(r'[أإآ]', 'ا', text)
    return text

def format_hadith_text(text):
    """Din befintliga formateringslogik med färger och symboler."""
    original_text = str(text).replace('\n', ' ')
    cleaned_text = original_text.replace('\ufffd', '').replace('ـ', '').replace('-', '')
    cleaned_text = re.sub(r'[^\u0020-\u007E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', cleaned_text)
    
    t = r'[\u064B-\u065F]*' 
    s = r'\s*'             
    y = f'[يى]{t}'        
    ra_base = f'ر{t}ض{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ن{t}ه{t}'
    master_pattern = f'(?P<saw>ص{t}ل{t}{y}{s}ا{t}ل{t}ل{t}ه{t}{s}ع{t}ل{t}ي{t}ه{t}{s}و{t}س{t}ل{t}م{t})|(?P<ra>{ra_base}(م{t}ا{t}|ا{t})?)|(?P<pink>ح{t}د{t}ث{t}ن{t}ا|ح{t}د{t}ث{t}ن{t}ي|عَن{t} )|(?P<orange>ق{t}ا{t}ل{t}ت? )'

    def repl(m):
        if m.lastgroup == 'saw': return '&nbsp;<span class="saw-symbol">ﷺ</span>'
        if m.lastgroup == 'ra': return '&nbsp;<span class="ra-symbol">ؓ</span>'
        if m.lastgroup == 'pink': return f'<span class="narrator-highlight">{m.group(0)}</span>'
        if m.lastgroup == 'orange': return f'<span class="qal-highlight">{m.group(0)}</span>'
        return m.group(0)

    formatted = re.sub(master_pattern, repl, cleaned_text)
    return formatted.strip()

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
    
    # Skapa kolumn för sökning (utan diakritiker)
    full_df['search_text'] = full_df['text'].apply(remove_diacritics)
    return full_df

df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---
tab1, tab2 = st.tabs(["🔢 Bläddra", "🔍 Sök"])

with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        sel_book = st.selectbox("Bok", ["Bukhari", "Muslim"], key="browse_book")
    with col2:
        h_id = st.number_input("Nummer", min_value=1, value=1, key="browse_id")
    
    results = df[(df['book_name'] == sel_book) & (df['hadithnumber'] == str(h_id))]

with tab2:
    search_query = st.text_input("Sök på arabiska (utan diakritiker)", placeholder="t.ex. انما الاعمال")
    if search_query:
        # Dela upp i ord och sök med "OCH"-logik
        words = search_query.split()
        mask = pd.Series([True] * len(df))
        for word in words:
            mask = mask & df['search_text'].str.contains(word, case=False, na=False)
        results = df[mask].head(20) # Begränsa till 20 för prestanda
    else:
        results = pd.DataFrame()

# --- VISA RESULTAT ---
if not results.empty:
    for _, row in results.iterrows():
        formatted_text = format_hadith_text(row['text'])
        st.markdown(f"""
        <div class="hadith-card">
            <div class="card-header">
                <span class="meta-tag">📖 {row['book_name']}</span>
                <span class="meta-tag"># {row['hadithnumber']}</span>
            </div>
            <div class="arabic-text">{formatted_text}</div>
        </div>
        """, unsafe_allow_html=True)
elif search_query:
    st.info("Inga träffar hittades för din sökning.")
