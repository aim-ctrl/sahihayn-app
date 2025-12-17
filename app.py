import streamlit as st
import pandas as pd
import requests
import html
import re

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer & Isnad Analyzer", page_icon="☪️", layout="centered")

# --- CSS / DESIGN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');
    
    #MainMenu { visibility: hidden !important; }
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; display: none !important; }
    
    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 24px;
        margin-top: 20px;
        border-right: 6px solid #2E8B57;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    
    .arabic-text {
        font-family: 'Scheherazade New', serif;
        font-size: 26px;
        line-height: 1.9;
        direction: rtl;
        text-align: right;
        color: #000;
        margin: 20px 0;
    }
    
    .arabic-text b { font-weight: 700; color: #2E8B57; }
    .qal-highlight { color: #ff8c00; font-weight: bold; }
    .narrator-highlight { color: #ec407a; font-weight: bold; }

    .card-header {
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        border-bottom: 1px solid #f5f5f5;
        padding-bottom: 15px;
    }

    .meta-tag {
        background-color: #f1f8e9;
        color: #2e7d32;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 700;
    }

    /* Isnad-stilar */
    .isnad-container {
        display: flex;
        flex-wrap: wrap;
        direction: rtl;
        gap: 10px;
        margin-top: 20px;
        justify-content: flex-start;
    }
    .isnad-node {
        background: #fdfdfd;
        border: 1px solid #ec407a;
        border-radius: 20px;
        padding: 5px 15px;
        font-family: 'Scheherazade New', serif;
        font-size: 18px;
        color: #333;
    }
    .isnad-arrow {
        color: #ec407a;
        align-self: center;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- HJÄLPFUNKTIONER FÖR ISNAD ---

def extract_isnad(text):
    """Extraherar berättarnamn genom att splitta på överföringstermer."""
    t = r'[\u064B-\u065F]*'
    # Vi klipper texten vid första citattecknet för att bara få isnad
    isnad_part = re.split(r'«|&quot;|“|"', text)[0]
    
    # Termer att splitta på
    split_terms = [
        f'ح{t}د{t}ث{t}ن{t}ا', f'ح{t}د{t}ث{t}ن{t}ي', 
        f'أ{t}خ{t}ب{t}ر{t}ن{t}ا', f'أ{t}خ{t}ب{t}ر{t}ن{t}ي', 
        f'عَن{t}', f'ق{t}ا{t}ل{t}'
    ]
    pattern = '|'.join(split_terms)
    
    # Splitta och rensa
    raw_nodes = re.split(pattern, isnad_part)
    # Ta bort korta fragment och städa whitespace
    clean_nodes = [n.strip() for n in raw_nodes if len(n.strip()) > 3]
    return clean_nodes

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
        except:
            return pd.DataFrame()

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

current_num_str = str(hadith_id)
result = df[(df['book_name'] == selected_book) & (df['hadithnumber'] == current_num_str)]

if not result.empty:
    row = result.iloc[0]
    raw_api_text = str(row['text'])
    display_text = raw_api_text.replace('\n', ' ')
    safe_text = html.escape(display_text)
    
    # --- FORMATTERING ---
    t = r'[\u064B-\u065F]*'
    orange_words = f'ف{t}ق{t}ا{t}ل{t} |ف{t}ق{t}ا{t}ل{t}ت{t} |ي{t}ق{t}و{t}ل{t} |ق{t}ا{t}ل{t}ت{t} |ق{t}ا{t}ل{t} '
    pink_words = f'ح{t}د{t}ث{t}ن{t}ا|ح{t}د{t}ث{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ي|أ{t}خ{t}ب{t}ر{t}ن{t}ا|عَن{t} '
    quote_str = r'&quot;.*?&quot;|«.*?»|“.*?”'
    
    master_pattern = f'(?P<quote>{quote_str})|(?P<pink>{pink_words})|(?P<orange>{orange_words})'

    def formatter_func(match):
        text = match.group(0)
        group_name = match.lastgroup
        if group_name == 'quote':
            inner = text.replace('&quot;', '').replace('«', '').replace('»', '').replace('“', '').replace('”', '')
            return f'«<b>{inner}</b>»'
        elif group_name == 'pink':
            return f'<span class="narrator-highlight">{text}</span>'
        elif group_name == 'orange':
            return f'<span class="qal-highlight">{text}</span>'
        return text

    formatted_text = re.sub(master_pattern, formatter_func, safe_text)

    # --- EXTRAHERA ISNAD ---
    isnad_nodes = extract_isnad(display_text)

    # --- VISA KORTET ---
    st.markdown(f"""
    <div class="hadith-card">
        <div class="card-header">
            <span class="meta-tag">📖 {row['book_name']}</span>
            <span class="meta-tag"># {row['hadithnumber']}</span>
        </div>
        <div class="arabic-text">{formatted_text}</div>
    </div>
    """, unsafe_allow_html=True)

    # --- VISA ISNAD-VISUALISERING ---
    if isnad_nodes:
        st.write("### 🔗 Berättarkedja (Isnad)")
        isnad_html = '<div class="isnad-container">'
        for i, node in enumerate(isnad_nodes):
            isnad_html += f'<div class="isnad-node">{node}</div>'
            if i < len(isnad_nodes) - 1:
                isnad_html += '<div class="isnad-arrow">←</div>'
        isnad_html += '</div>'
        st.markdown(isnad_html, unsafe_allow_html=True)

    with st.expander("Se rådata"):
        st.code(raw_api_text)
else:
    st.info(f"Nummer {current_num_str} hittades inte.")
