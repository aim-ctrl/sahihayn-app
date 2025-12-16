import streamlit as st
import pandas as pd
import requests
import html

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Lookup", page_icon="☪️", layout="centered")

# --- CSS / DESIGN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');
    
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
    
    # --- NYTT: STÄDA NUMREN ---
    # 1. Gör om allt till text (strängar)
    full_df['hadithnumber'] = full_df['hadithnumber'].astype(str)
    # 2. Ta bort ".0" om det finns (t.ex. "1.0" blir "1")
    full_df['hadithnumber'] = full_df['hadithnumber'].str.replace('.0', '', regex=False)
    
    return full_df

with st.spinner("Laddar biblioteket..."):
    df = get_dataset()

# --- UI ---

st.title("📖 Hadith Viewer")

col1, col2 = st.columns([1, 1])
with col1:
    selected_book = st.selectbox("Välj Bok", ["Bukhari", "Muslim"])
with col2:
    input_number = st.text_input("Hadith Nummer", placeholder="T.ex. 1")

# --- DEBUGGER (Hjälper oss se vad som är fel) ---
with st.expander("🔍 Se hur datan ser ut (Debug)"):
    st.write(f"Totalt antal hadither laddade: {len(df)}")
    # Visa de första 5 raderna för den valda boken så vi ser numreringen
    st.write(f"Exempel från {selected_book}:")
    st.dataframe(df[df['book_name'] == selected_book].head(5))

# --- SÖKNING ---
if input_number:
    # Städa inputen också (ta bort mellanslag)
    clean_input = input_number.strip()
    
    # Filtrera
    result = df[
        (df['book_name'] == selected_book) & 
        (df['hadithnumber'] == clean_input)
    ]

    if not result.empty:
        row = result.iloc[0]
        arabic_text = html.escape(str(row['text'])).replace('\n', ' ')
        
        card_html = f"""<div class="hadith-card"><div class="card-header"><span class="meta-tag">📖 {row['book_name']}</span><span class="meta-tag"># {row['hadithnumber']}</span></div><div class="arabic-text">{arabic_text}</div></div>"""
        st.markdown(card_html, unsafe_allow_html=True)
        
    else:
        st.warning(f"Ingen träff på nummer **{clean_input}** i **{selected_book}**.")
        # Visa tips om vad som faktiskt finns nära
        st.info("Kolla i 'Debug'-lådan ovan för att se hur numren ser ut i databasen.")
