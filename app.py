import streamlit as st
import pandas as pd
import requests
import html

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Viewer", page_icon="☪️", layout="centered")

# --- INITIALISERA STATE (Minnet) ---
# Vi måste starta räknaren på 1 om den inte redan finns
if 'hadith_number' not in st.session_state:
    st.session_state.hadith_number = 1

# --- CALLBACKS (Knapp-funktioner) ---
def next_hadith():
    st.session_state.hadith_number += 1

def prev_hadith():
    if st.session_state.hadith_number > 1:
        st.session_state.hadith_number -= 1

# --- CSS / DESIGN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');
    
    /* Justera inmatningsfältet så det ser ut som en räknare */
    div[data-testid="stNumberInput"] input {
        text-align: center;
        font-size: 20px;
        font-weight: bold;
    }

    /* Gör knapparna lite bredare */
    div[data-testid="stButton"] button {
        width: 100%;
        font-size: 20px;
    }

    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 24px;
        margin-top: 20px;
        border-right: 6px solid #2E8B57;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
    }
    
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

    .card-header {
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        border-bottom: 1px solid #f5f5f5;
        padding-bottom: 15px;
        direction: ltr; 
    }

    .meta-tag {
        background-color: #f1f8e9;
        color: #2e7d32;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 700;
        border: 1px solid #dcedc8;
    }
    
    /* Dölj Streamlits inbyggda små pilar i nummer-fältet för en renare look */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { 
        -webkit-appearance: none; 
        margin: 0; 
    }
</style>
""", unsafe_allow_html=True)

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
    
    # Städa numren (ta bort .0 och gör till text)
    full_df['hadithnumber'] = full_df['hadithnumber'].astype(str).str.replace('.0', '', regex=False)
    
    return full_df

with st.spinner("Laddar biblioteket..."):
    df = get_dataset()

# --- UI ---

st.title("📖 Hadith Viewer")

# 1. Välj bok (Radio Buttons)
selected_book = st.radio(
    "Välj Bok", 
    ["Bukhari", "Muslim"], 
    horizontal=True
)

st.write("") # Lite luft

# 2. Navigering (Minus | Input | Plus)
col_minus, col_input, col_plus = st.columns([1, 2, 1])

with col_minus:
    st.button("➖", on_click=prev_hadith)

with col_input:
    # Koppla input direkt till st.session_state.hadith_number
    st.number_input(
        "Nummer", 
        min_value=1, 
        step=1, 
        key="hadith_number", # Detta kopplar inputen till minnet
        label_visibility="collapsed" # Döljer etiketten "Nummer" för snyggare design
    )

with col_plus:
    st.button("➕", on_click=next_hadith)

# --- VISA KORTET ---

# Hämta nuvarande nummer från minnet
current_num_str = str(st.session_state.hadith_number)

# Sök i datan
result = df[
    (df['book_name'] == selected_book) & 
    (df['hadithnumber'] == current_num_str)
]

if not result.empty:
    row = result.iloc[0]
    arabic_text = html.escape(str(row['text'])).replace('\n', ' ')
    
    card_html = f"""<div class="hadith-card"><div class="card-header"><span class="meta-tag">📖 {row['book_name']}</span><span class="meta-tag"># {row['hadithnumber']}</span></div><div class="arabic-text">{arabic_text}</div></div>"""
    st.markdown(card_html, unsafe_allow_html=True)
    
else:
    st.info(f"Nummer **{current_num_str}** finns inte i **{selected_book}** (eller så har den ett annat format, t.ex. '1a').")
