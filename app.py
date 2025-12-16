import streamlit as st
import pandas as pd
import requests
import html

# --- KONFIGURATION ---
st.set_page_config(
    page_title="Hadith Lookup", 
    page_icon="☪️", 
    layout="centered"
)

# --- CSS / DESIGN (Din specifika stil) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');

    /* Design av sökfält och input */
    .stTextInput > div > div > input {
        text-align: center; 
        font-size: 18px;
    }
    
    /* Kortet */
    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 24px;
        margin-top: 20px;
        border-right: 6px solid #2E8B57; /* RTL-accent */
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
    }
    
    /* Arabisk text */
    .arabic-text {
        font-family: 'Scheherazade New', serif;
        font-size: 38px;
        line-height: 2.2;
        direction: rtl;
        text-align: right;
        color: #000;
        margin-top: 20px;
        width: 100%;
    }

    /* Header inuti kortet */
    .card-header {
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        border-bottom: 1px solid #f5f5f5;
        padding-bottom: 15px;
        direction: ltr; /* Metadata från vänster till höger */
    }

    .meta-tag {
        background-color: #f1f8e9;
        color: #2e7d32;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 700;
        border: 1px solid #dcedc8;
        letter-spacing: 0.5px;
    }

    /* Mörkt läge */
    @media (prefers-color-scheme: dark) {
        .hadith-card { background-color: #1e1e1e; border-color: #333; }
        .arabic-text { color: #ffffff; }
        .meta-tag { background-color: #1b3320; color: #a5d6a7; border-color: #2e5c35; }
        .card-header { border-bottom-color: #333; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATALOGIK ---

@st.cache_data(show_spinner=False)
def get_dataset():
    """Hämtar Bukhari och Muslim (Endast Arabiska versionen)"""
    
    def load_book(book_name):
        # Vi hämtar den arabiska JSON-filen
        url = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        try:
            resp = requests.get(url).json()
            df = pd.DataFrame(resp['hadiths'])
            df['book_name'] = book_name.capitalize()
            # Se till att hadithnumber behandlas som text så vi kan matcha exakt
            df['hadithnumber'] = df['hadithnumber'].astype(str)
            return df
        except:
            return pd.DataFrame()

    df_bukhari = load_book("bukhari")
    df_muslim = load_book("muslim")
    
    return pd.concat([df_bukhari, df_muslim], ignore_index=True)

# Ladda data i bakgrunden
with st.spinner("Laddar biblioteket..."):
    df = get_dataset()

# --- ANVÄNDARGRÄNSSNITT ---

st.title("📖 Hadith Viewer")

# Layout med kolumner för inputs
col1, col2 = st.columns([1, 1])

with col1:
    selected_book = st.selectbox("Välj Bok", ["Bukhari", "Muslim"])

with col2:
    # Text input fungerar bäst eftersom vissa hadither heter "1a" eller liknande
    input_number = st.text_input("Hadith Nummer", placeholder="T.ex. 1, 45, 102...")

# Logik för att visa kortet
if input_number:
    # Filtrera dataframen
    result = df[
        (df['book_name'] == selected_book) & 
        (df['hadithnumber'] == input_number.strip())
    ]

    if not result.empty:
        row = result.iloc[0] # Ta första träffen
        
        # Städa texten
        arabic_text = html.escape(str(row['text'])).replace('\n', ' ')
        
        # Bygg HTML-kortet
        # OBS: Inga mellanslag/indrag i början av raderna i f-stringen!
        card_html = f"""<div class="hadith-card"><div class="card-header"><span class="meta-tag">📖 {row['book_name']}</span><span class="meta-tag"># {row['hadithnumber']}</span></div><div class="arabic-text">{arabic_text}</div></div>"""

        st.markdown(card_html, unsafe_allow_html=True)
        
    else:
        st.warning(f"Kunde inte hitta hadith nummer **{input_number}** i **{selected_book}**.")
        st.caption("Tips: Kontrollera numreringen. API:et använder den internationella standardnumreringen.")
