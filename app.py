import streamlit as st
import pandas as pd
from thefuzz import process

# --- KONFIGURATION OCH DESIGN ---
st.set_page_config(page_title="Hadith Sök", layout="centered")

# Anpassad CSS för att skapa "Cards" design och RTL för arabiska
st.markdown("""
<style>
    .hadith-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #4CAF50;
    }
    .arabic-text {
        font-family: 'Amiri', serif;
        font-size: 22px;
        direction: rtl;
        text-align: right;
        color: #333;
        margin-bottom: 15px;
    }
    .swedish-text {
        font-size: 16px;
        color: #555;
        margin-bottom: 10px;
        font-style: italic;
    }
    .meta-data {
        font-size: 12px;
        color: #888;
        border-top: 1px solid #eee;
        padding-top: 10px;
        display: flex;
        justify-content: space-between;
    }
    .tag {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
    }
    /* Mörkt läge-stöd (enkel variant) */
    @media (prefers-color-scheme: dark) {
        .hadith-card { background-color: #1e1e1e; }
        .arabic-text { color: #e0e0e0; }
        .swedish-text { color: #b0b0b0; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATA (Här simulerar vi din databas) ---
# I framtiden byter vi ut detta mot: df = pd.read_csv('hadither.csv')
def load_data():
    data = [
        {
            "id": 1,
            "arabic": "إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ",
            "swedish": "Handlingar bedöms endast efter avsikterna.",
            "source": "Bukhari & Muslim",
            "isnad": "Umar bin Al-Khattab",
            "grade": "Sahih (Muttafaqun Alayhi)",
            "category": "Avsikt",
            "topic": "Niyyah"
        },
        {
            "id": 2,
            "arabic": "الدِّينُ النَّصِيحَةُ",
            "swedish": "Religionen är uppriktighet (nasiha).",
            "source": "Muslim (liknande i Bukhari)",
            "isnad": "Tamim Ad-Dari",
            "grade": "Sahih",
            "category": "Karaktär",
            "topic": "Råd"
        },
         {
            "id": 3,
            "arabic": "لَا يُؤْمِنُ أَحَدُكُمْ حَتَّى يُحِبَّ لِأَخِيهِ مَا يُحِبُّ لِنَفْسِهِ",
            "swedish": "Ingen av er är en (fullkomlig) troende förrän han önskar för sin broder vad han önskar för sig själv.",
            "source": "Bukhari & Muslim",
            "isnad": "Anas bin Malik",
            "grade": "Sahih (Muttafaqun Alayhi)",
            "category": "Broderlighet",
            "topic": "Tro"
        }
    ]
    return pd.DataFrame(data)

df = load_data()

# --- HUVUDFUNKTIONER ---

def search_hadith(query, dataframe):
    if not query:
        return dataframe
    
    query = query.lower()
    
    # Exakt matchning först
    mask = (
        dataframe['swedish'].str.lower().str.contains(query) |
        dataframe['category'].str.lower().str.contains(query) |
        dataframe['topic'].str.lower().str.contains(query)
    )
    results = dataframe[mask]
    
    # Om inga träffar, prova fuzzy search (lite variation) på svenska texten
    if results.empty:
        # Hämta alla svenska meningar
        all_swedish = dataframe['swedish'].tolist()
        # Hitta bästa matchningar (limit=5)
        matches = process.extract(query, all_swedish, limit=5)
        # Filtrera de som har minst 60% likhet
        good_matches = [m[0] for m in matches if m[1] > 60]
        results = dataframe[dataframe['swedish'].isin(good_matches)]
        
    return results

# --- APPLIKATIONENS UI ---

st.title("📚 Hadith Sök")
st.caption("Sök i Bukhari & Muslim (Muttafaqun Alayhi)")

# Sökfält
search_query = st.text_input("Sök på ord, mening eller ämne...", placeholder="T.ex. avsikt, bön, tro...")

# Filtrering (Valfritt)
selected_category = st.multiselect("Filtrera på kategori", options=df['category'].unique())

# Logik för filtrering
filtered_df = search_hadith(search_query, df)

if selected_category:
    filtered_df = filtered_df[filtered_df['category'].isin(selected_category)]

# Visa resultat
st.markdown(f"**Hittade {len(filtered_df)} hadither**")

for index, row in filtered_df.iterrows():
    # Här skapar vi HTML-kortet för varje hadith
    st.markdown(f"""
    <div class="hadith-card">
        <div class="tag">{row['category']} | {row['topic']}</div>
        <div class="arabic-text">{row['arabic']}</div>
        <div class="swedish-text">"{row['swedish']}"</div>
        <div class="meta-data">
            <span><strong>Källa:</strong> {row['source']}</span>
            <span><strong>Grad:</strong> {row['grade']}</span>
        </div>
        <div class="meta-data" style="border:none; padding-top:0;">
            <span><em>Isnad: {row['isnad']}</em></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("Källkod på GitHub. Data baserad på Sahih Bukhari och Muslim.")
