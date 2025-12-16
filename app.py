import streamlit as st
import pandas as pd
import requests
import html
from thefuzz import process

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Hadith Search Engine", 
    page_icon="☪️", 
    layout="centered"
)

# --- CSS / STYLING ---
st.markdown("""
<style>
    /* 1. IMPORTERA FONTEN FRÅN GOOGLE */
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');

    /* Card Design */
    .hadith-card {
        background-color: var(--background-color);
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        border-left: 6px solid #2E8B57; /* SeaGreen */
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
        /* Fix för layout-problem */
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    
    .hadith-card:hover {
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    
    /* Arabic Text Styling - UPDATED */
    .arabic-text {
        font-family: 'Scheherazade New', serif; /* Här är din nya font */
        font-size: 32px; /* Ökad storlek för läsbarhet */
        line-height: 2.0; /* Luftigare rader */
        direction: rtl;
        text-align: right;
        color: #1f1f1f;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 1px dashed #eee;
        width: 100%;
        display: block;
    }
    
    /* English Text Styling */
    .english-text {
        font-family: 'Source Sans Pro', sans-serif;
        font-size: 17px;
        line-height: 1.6;
        color: #444;
        margin-bottom: 12px;
        direction: ltr;
        text-align: left;
    }

    /* Meta Data Tags */
    .meta-tag {
        display: inline-block;
        background-color: #f1f8e9;
        color: #33691e;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 8px;
        margin-bottom: 8px; /* Om de radbryts */
        border: 1px solid #dcedc8;
    }

    /* Dark Mode Support */
    @media (prefers-color-scheme: dark) {
        .hadith-card { background-color: #262730; border-color: #444; }
        .arabic-text { color: #e0e0e0; border-bottom-color: #444; }
        .english-text { color: #c0c0c0; }
        .meta-tag { background-color: #1b3320; color: #a5d6a7; border-color: #2e5c35; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATA FETCHING ---

@st.cache_data(show_spinner=True)
def load_data():
    """
    Fetches English and Arabic editions of Bukhari and Muslim from API.
    Merges them based on hadith number.
    """
    
    def fetch_book_pair(book_name):
        # API Endpoints
        url_eng = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/eng-{book_name}.json"
        url_ara = f"https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{book_name}.json"
        
        try:
            # Fetch both languages
            resp_eng = requests.get(url_eng).json()
            resp_ara = requests.get(url_ara).json()
            
            # Create DataFrames
            df_eng = pd.DataFrame(resp_eng['hadiths'])
            df_ara = pd.DataFrame(resp_ara['hadiths'])
            
            # Map Arabic text to English DataFrame using 'hadithnumber' as key
            ara_map = dict(zip(df_ara['hadithnumber'], df_ara['text']))
            
            df_eng['arabic_text'] = df_eng['hadithnumber'].map(ara_map)
            df_eng['source_book'] = book_name.capitalize()
            
            # Clean data (remove rows missing text in either language)
            df_eng = df_eng.dropna(subset=['text', 'arabic_text'])
            
            # Return specific columns
            return df_eng[['source_book', 'hadithnumber', 'text', 'arabic_text', 'grades']]
            
        except Exception as e:
            st.error(f"Error fetching {book_name}: {e}")
            return pd.DataFrame()

    # Fetch both books
    df_bukhari = fetch_book_pair("bukhari")
    df_muslim = fetch_book_pair("muslim")
    
    # Combine into one dataset
    return pd.concat([df_bukhari, df_muslim], ignore_index=True)

# Initialize Data
try:
    with st.spinner('Downloading Hadith database... please wait...'):
        df = load_data()
except Exception as e:
    st.error("Failed to load data. Please check your internet connection.")
    df = pd.DataFrame()

# --- SEARCH LOGIC ---

def search_engine(query, data, method):
    if not query:
        # Return a random sample if no query is present
        return data.sample(10)
    
    query = query.lower().strip()
    
    if method == "Exact Match":
        # Search in English text, Arabic text, or Hadith Number
        mask = (
            data['text'].str.lower().str.contains(query, na=False) |
            data['arabic_text'].str.contains(query, na=False) |
            data['hadithnumber'].astype(str).str.contains(query, na=False)
        )
        return data[mask]
    
    elif method == "Fuzzy Search (Smart)":
        # Uses Levenshtein distance to find approximate matches (mainly for English)
        titles = data['text'].tolist()
        # Get top 20 matches
        matches = process.extract(query, titles, limit=20)
        # Filter for quality matches (>60 score)
        match_texts = [m[0] for m in matches if m[1] >= 60]
        return data[data['text'].isin(match_texts)]

# --- UI LAYOUT ---

st.title("📚 Hadith Search")
st.markdown("Search across **Sahih Bukhari** & **Sahih Muslim**.")

# Sidebar Settings
with st.sidebar:
    st.header("Settings")
    
    # Book Filter
    selected_books = st.multiselect(
        "Select Books", 
        options=["Bukhari", "Muslim"], 
        default=["Bukhari", "Muslim"]
    )
    
    # Search Mode
    search_mode = st.radio(
        "Search Method", 
        ["Exact Match", "Fuzzy Search (Smart)"]
    )
    
    st.info("""
    **Exact Match:** Finds the exact word or phrase (supports Arabic & English).
    
    **Fuzzy Search:** Finds similar words even with spelling mistakes (best for English).
    """)

# Filter Data by Book
filtered_df = df[df['source_book'].isin(selected_books)]

# Search Input
query = st.text_input(
    "Search", 
    placeholder="Type a topic (e.g., 'Fasting'), Arabic word (e.g., 'صلاة'), or number..."
)

# Execute Search
results = search_engine(query, filtered_df, search_mode)

# Results Header
st.markdown(f"**Found {len(results)} Hadiths**")

# Display Results (Limit to 50 to prevent lag)
display_limit = 50

# Loopa igenom resultaten
for i, row in results.head(display_limit).iterrows():
    
    # 1. SÄKERHETSSTÄDA TEXTEN
    # html.escape gör om " och ' till ofarlig kod så de inte kraschar HTML-strukturen
    arabic_safe = html.escape(str(row['arabic_text'])).replace('\n', ' ')
    english_safe = html.escape(str(row['text'])).replace('\n', '<br>')
    
    # Hantera Grade
    grade_badge = ""
    if isinstance(row['grades'], list) and len(row['grades']) > 0:
        try:
            g = row['grades'][0]['grade']
            grade_badge = f"<span class='meta-tag' style='background-color:#fff3e0; color:#e65100; border-color:#ffe0b2;'>{g}</span>"
        except:
            pass

    # 2. BYGG HTML-KODEN (OBS: INGEN INDRAGNING PÅ RADErna NEDAN!)
    # Vi trycker koden mot vänsterkanten för att inte förvirra Streamlit
    card_html = f"""
<div class="hadith-card">
<div style="margin-bottom:15px;">
<span class="meta-tag">📖 {row['source_book']}</span>
<span class="meta-tag"># {row['hadithnumber']}</span>
{grade_badge}
</div>
<div class="arabic-text">{arabic_safe}</div>
<div class="english-text">{english_safe}</div>
</div>
"""

    # 3. RENDERA
    st.markdown(card_html, unsafe_allow_html=True)

if len(results) > display_limit:
    st.warning(f"Showing the first {display_limit} results. Please refine your search to see more.")

# Footer
st.markdown("---")
st.caption("Data source: fawazahmed0 Hadith API | Built with Streamlit")
