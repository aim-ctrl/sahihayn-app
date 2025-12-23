import streamlit as st
import pandas as pd
import requests
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer", page_icon="☪️", layout="centered")

# --- CSS / DESIGN ---
# (Här klistrar du in hela din <style>-block från ditt ursprungliga inlägg)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');
    /* ... [Resten av din CSS] ... */
    .hadith-card { margin-bottom: 30px; } /* Lagt till lite extra marginal mellan korten */
</style>
""", unsafe_allow_html=True)

# --- HJÄLPFUNKTIONER ---
def remove_diacritics(text):
    """Tar bort arabiska diakritiker för sökning."""
    if not isinstance(text, str): return ""
    # Regex för att ta bort: fatha, damma, kasra, sukun, shadda, tanween
    pattern = re.compile(r'[\u064B-\u0652]')
    return re.sub(pattern, '', text)

def apply_custom_formatting(original_text):
    """Din specifika formateringslogik."""
    # 1. Städning
    cleaned_text = str(original_text).replace('\ufffd', '').replace('ـ', '').replace('-', '').replace('\n', ' ')
    cleaned_text = re.sub(r'[^\u0020-\u007E\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', '', cleaned_text)

    # 2. Mönster för formatering
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
    formatted_text = re.sub(r'\s+', ' ', formatted_text).strip()
    return formatted_text

# --- DATALOGIK ---
@st.cache_data(show_spinner=False)
def get_dataset():
    def load_book(book_name):
        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        try:
            resp = requests.get(url).json()
            df = pd.DataFrame(resp['hadiths'])
            df['book_name'] = book_name.capitalize()
            # Skapa sökbar text genom att ta bort diakritiker vid laddning
            df['search_clean'] = df['text'].apply(remove_diacritics)
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
st.title("Hadith Sök & Bläddra")

# Skapa två flikar: en för sökning och en för att bläddra via nummer
tab_search, tab_browse = st.tabs(["🔍 Sök på text", "🔢 Bläddra per nummer"])

with tab_search:
    query = st.text_input("Sök (ange flera ord för 'och'-logik):", placeholder="t.ex. انما الاعمال")
    results = pd.DataFrame()
    
    if query:
        words = query.split()
        # Starta med alla rader, filtrera sedan för varje ord
        mask = pd.Series([True] * len(df))
        for word in words:
            mask = mask & df['search_clean'].str.contains(word, na=False)
        results = df[mask]

with tab_browse:
    col1, col2 = st.columns(2)
    with col1:
        selected_book = st.radio("Välj bok", ["Bukhari", "Muslim"], horizontal=True)
    with col2:
        hadith_id = st.number_input("Hadith Nummer", min_value=1, value=1, step=1)
    
    if not query: # Visa bara browse-resultat om användaren inte söker
        results = df[(df['book_name'] == selected_book) & (df['hadithnumber'] == str(hadith_id))]

# --- RENDERING AV KORT ---
if not results.empty:
    st.write(f"Hittade {len(results)} hadither:")
    for _, row in results.iterrows():
        # Kör din formateringslogik på texten
        display_text = apply_custom_formatting(row['text'])
        
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
elif query:
    st.warning("Inga träffar hittades.")
