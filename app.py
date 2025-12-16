import streamlit as st
import pandas as pd
import requests
from thefuzz import process

# --- KONFIGURATION ---
st.set_page_config(page_title="Hadith Search", page_icon="☪️", layout="centered")

# --- CSS / DESIGN ---
st.markdown("""
<style>
    /* Kort-design */
    .hadith-card {
        background-color: var(--background-color);
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 24px;
        border-left: 6px solid #2E8B57; /* SeaGreen */
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Arabisk textdesign */
    .arabic-text {
        font-family: 'Amiri', 'Traditional Arabic', serif;
        font-size: 24px;
        line-height: 1.8;
        direction: rtl;
        text-align: right;
        color: #1f1f1f;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 1px dashed #eee;
    }
    
    /* Engelsk textdesign */
    .english-text {
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 16px;
        line-height: 1.5;
        color: #444;
        margin-bottom: 12px;
    }

    /* Metadata (Källa, nummer) */
    .meta-tag {
        display: inline-block;
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 5px;
    }

    /* Dark mode anpassning */
    @media (prefers-color-scheme: dark) {
        .hadith-card { background-color: #262730; border-color: #444; }
        .arabic-text { color: #e0e0e0; border-bottom-color: #444; }
        .english-text { color: #c0c0c0; }
        .meta-tag { background-color: #1e3a29; color: #81c784; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATAFUNKTIONER ---

@st.cache_data(show_spinner=True)
def load_and_merge_data():
    """Hämtar Bukhari och Muslim (Eng + Ara) och slår ihop dem."""
    
    def fetch_book(book_name):
        # URL:er till API
        url_eng = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-{book_name}.json"
        url_ara = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        
        try:
            # Hämta båda språken
            resp_eng = requests.get(url_eng).json()
            resp_ara = requests.get(url_ara).json()
            
            # Skapa DataFrames
            df_eng = pd.DataFrame(resp_eng['hadiths'])
            df_ara = pd.DataFrame(resp_ara['hadiths'])
            
            # Förbered arabiska för sammanslagning (använd hadithnumber som nyckel)
            # Vi gör en dictionary för snabb uppslagning: {hadithnumber: text}
            ara_map = dict(zip(df_ara['hadithnumber'], df_ara['text']))
            
            # Lägg till arabisk text i den engelska dataframen
            df_eng['arabic_text'] = df_eng['hadithnumber'].map(ara_map)
            df_eng['source_book'] = book_name.capitalize()
            
            # Rensa bort rader som saknar text
            df_eng = df_eng.dropna(subset=['text', 'arabic_text'])
            
            return df_eng[['source_book', 'hadithnumber', 'text', 'arabic_text', 'grades']]
            
        except Exception as e:
            st.error(f"Kunde inte ladda {book_name}: {e}")
            return pd.DataFrame()

    # Hämta data
    df_bukhari = fetch_book("bukhari")
    df_muslim = fetch_book("muslim")
    
    # Slå ihop allt
    full_df = pd.concat([df_bukhari, df_muslim], ignore_index=True)
    return full_df

# Ladda datan (Detta sker bara en gång per session)
try:
    with st.spinner('Hämtar hadither från databasen...'):
        df = load_and_merge_data()
except Exception as e:
    st.error("Ett fel uppstod vid laddning av data. Kontrollera din internetanslutning.")
    df = pd.DataFrame()

# --- SÖKLOGIK ---

def search_engine(query, data, search_mode):
    if not query:
        return data.sample(10) # Visa 10 slumpmässiga om ingen sökning görs
    
    query = query.lower()
    
    if search_mode == "Exakt matchning":
        # Snabb sökning
        mask = (
            data['text'].str.lower().str.contains(query, na=False) |
            data['arabic_text'].str.contains(query, na=False) |
            data['hadithnumber'].astype(str).str.contains(query, na=False)
        )
        return data[mask]
    
    elif search_mode == "Fuzzy (Smart sök)":
        # Lite långsammare men hittar "nästan" rätt ord
        # Vi söker endast i engelska texten för prestanda i detta läge
        titles = data['text'].tolist()
        matches = process.extract(query, titles, limit=20)
        # Vi accepterar träffar med över 60% likhet
        match_texts = [m[0] for m in matches if m[1] >= 60]
        return data[data['text'].isin(match_texts)]

# --- UI LAYOUT ---

st.title("📖 Hadith Explorer")
st.caption("Sök i Sahih Bukhari & Sahih Muslim (Engelska & Arabiska)")

# Sidebar filter
with st.sidebar:
    st.header("Inställningar")
    selected_books = st.multiselect(
        "Välj böcker", 
        options=["Bukhari", "Muslim"], 
        default=["Bukhari", "Muslim"]
    )
    search_mode = st.radio("Sökmetod", ["Exakt matchning", "Fuzzy (Smart sök)"])
    st.info("💡 **Fuzzy sök** hittar resultat även om du stavar lite fel, men är långsammare.")

# Filtrera på bok först
filtered_df = df[df['source_book'].isin(selected_books)]

# Sökfält
search_query = st.text_input("", placeholder="Sök på ord (t.ex. 'Prayer', 'Intention') eller hadith-nummer...")

# Utför sökning
results = search_engine(search_query, filtered_df, search_mode)

# Visa resultat
st.markdown(f"**Visar {len(results)} hadither**")

# Loopa igenom och rendera kort
# Vi sätter en gräns på 50 kort för att inte krascha webbläsaren om man söker på "the"
for i, row in results.head(50).iterrows():
    
    # Hantera Grade (om det finns)
    grade_display = ""
    if isinstance(row['grades'], list) and len(row['grades']) > 0:
        # Ta första graden som exempel
        grade_display = f"<span class='meta-tag' style='background-color:#fff3e0; color:#e65100;'>{row['grades'][0]['grade']}</span>"

    st.markdown(f"""
    <div class="hadith-card">
        <div style="margin-bottom:10px;">
            <span class="meta-tag">{row['source_book']}</span>
            <span class="meta-tag">#{row['hadithnumber']}</span>
            {grade_display}
        </div>
        <div class="arabic-text">{row['arabic_text']}</div>
        <div class="english-text">{row['text']}</div>
    </div>
    """, unsafe_allow_html=True)

if len(results) > 50:
    st.warning("Visar de första 50 resultaten. Förfina din sökning för att se mer.")

# Footer
st.markdown("---")
st.caption("Data provided by fawazahmed0 API.")
