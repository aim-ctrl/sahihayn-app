import html
import re
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
import streamlit as st
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# KONFIGURATION
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Hadith Viewer & Sök", page_icon="☪️", layout="centered")

PAGE_SIZE = 20  # antal hadither som visas åt gången
API_URL = "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-{slug}.json"
BOOKS = [
    ("bukhari", "Sahih Bukhari"),
    ("muslim", "Sahih Muslim"),
    ("abudawud", "Sunan Abu Dawood"),
    ("tirmidhi", "Jami' At-Tirmidhi"),
    ("nasai", "Sunan An-Nasa'i"),
    ("ibnmajah", "Sunan Ibn Majah"),
]

for _key, _default in {
    "active_book_filter": None,
    "last_query": "",
    "visible_count": PAGE_SIZE,
}.items():
    st.session_state.setdefault(_key, _default)

# ---------------------------------------------------------------------------
# REGLER FÖR TEXTHANTERING
# ---------------------------------------------------------------------------
TASHKEEL = r"[\u064B-\u065F\u0670]*"  # vokaltecken (valfria mellan bokstäver)
SPACES = r"\s*"
ALIF_CHARS = "اأإآٱ"
YA_CHARS = "يى"


def loose_word(word: str) -> str:
    """Bygger ett regex som matchar ordet oavsett tashkeel och alif/ya-varianter."""
    parts = []
    for ch in word:
        if ch.isspace():
            parts.append(r"\s+")
        elif ch in ALIF_CHARS:
            parts.append(f"[{ALIF_CHARS}]{TASHKEEL}")
        elif ch in YA_CHARS:
            parts.append(f"[{YA_CHARS}]{TASHKEEL}")
        else:
            parts.append(f"{re.escape(ch)}{TASHKEEL}")
    return "".join(parts)


def any_of(*words: str) -> str:
    return "|".join(loose_word(w) for w in words)


SALLALLAH = SPACES.join(loose_word(w) for w in ("صلى", "الله", "عليه", "وسلم"))
RASUL_ALLAH = loose_word("رسول") + SPACES + loose_word("الله")

# "رضي الله عنه / عنها / عنهما / عنهم / عنهن" (även med "تعالى")
RADI_ALLAH = (
    loose_word("رضي")
    + SPACES
    + loose_word("الله")
    + rf"(?:{SPACES}{loose_word('تعالى')})?"
    + SPACES
    + loose_word("عنه")
    + f"(?:{any_of('ما', 'م', 'ن', 'ا')})?"
)

PINK_WORDS = any_of("حدثنا", "حدثني", "أخبرني", "أخبرنا", "سمعت") + "|" + loose_word("عن") + r"\s"
ORANGE_WORDS = "|".join(loose_word(w) + r"\s" for w in ("فقال", "فقالت", "يقول", "قالت", "قال"))
QUOTE_STR = r'".*?"|«.*?»|“.*?”'
CURLY_BRACES = r"\{.*?\}"

MASTER_PATTERN = re.compile(
    rf"(?P<quote>{QUOTE_STR})|(?P<saw>{SALLALLAH})|(?P<ra>{RADI_ALLAH})|"
    rf"(?P<pink>{PINK_WORDS})|(?P<orange>{ORANGE_WORDS})|"
    rf"(?P<red>{RASUL_ALLAH})|(?P<curly>{CURLY_BRACES})"
)

SPAN_CLASSES = {
    "pink": "narrator-highlight",
    "orange": "qal-highlight",
    "red": "rasul-highlight",
    "curly": "curly-highlight",
}

# Tillåtna tecken vid visning (ASCII, arabiska block och citattecken « » “ ”)
NOISE_RE = re.compile(
    r"[^\u0020-\u007E\u00AB\u00BB\u201C\u201D"
    r"\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
MARKS_RE = re.compile(r"[\u064B-\u065F\u0670\u0640]")  # tashkeel + tatweel
ALIF_RE = re.compile(f"[{ALIF_CHARS}]")
TAG_SPLIT_RE = re.compile(r"(<[^>]+>|&#?\w+;)")


# ---------------------------------------------------------------------------
# CSS / DESIGN
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Scheherazade+New:wght@400;700&display=swap');

    #MainMenu { visibility: hidden !important; }
    header { visibility: hidden !important; }
    footer { visibility: hidden !important; display: none !important; }

    .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }

    /* --- Sökfält --- */
    .stTextInput input, .stTextInput input::placeholder { direction: rtl; text-align: right; }
    [data-testid="InputInstructions"] { display: none !important; }

    /* --- Kompakta knappar --- */
    [data-testid="column"], [data-testid="stColumn"] { padding: 0; }
    [data-testid="column"] > div, [data-testid="stColumn"] > div { gap: 0.25rem !important; }
    div.stButton { margin-bottom: 0; }
    div.stButton > button {
        width: 100%;
        border-radius: 6px;
        padding: 2px 4px;
        min-height: 0;
        height: auto;
        line-height: 1.2;
    }
    div.stButton > button p { font-size: 11px; line-height: 1.2; margin: 0; }

    /* --- Hadith-kort --- */
    .hadith-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 25px;
        border-right: 6px solid #2E8B57;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
    }
    .card-header {
        display: flex; justify-content: space-between; align-items: center;
        border-bottom: 1px solid #f5f5f5; padding-bottom: 15px; margin-bottom: 15px;
        direction: ltr;
    }
    .meta-tag {
        background-color: #f1f8e9; color: #2e7d32; padding: 6px 14px;
        border-radius: 8px; font-size: 0.75rem; font-weight: 700;
        border: 1px solid #dcedc8; white-space: nowrap;
    }
    .arabic-text {
        font-family: 'Scheherazade New', serif;
        font-size: 18px;
        line-height: 1.7;
        direction: rtl;
        text-align: right;
        color: #1a1a1a;
        width: 100%;
    }
    .arabic-text b { font-weight: 700; color: #2E8B57; }
    .qal-highlight { color: #ff8c00; font-weight: bold; }
    .narrator-highlight { color: #ec407a; font-weight: bold; }
    .rasul-highlight { color: #d32f2f; font-weight: bold; }
    .curly-highlight { color: #0328fc; font-weight: bold; }
    .search-highlight {
        background-color: #fff59d; border-radius: 4px; padding: 0 2px;
        box-shadow: 0 0 2px rgba(0,0,0,0.1);
    }
    .saw-symbol, .ra-symbol { font-family: 'Scheherazade New', serif; font-size: 0.9em; margin-right: 4px; }
    .saw-symbol { color: #d32f2f; }
    .ra-symbol { color: #000000; font-weight: normal; }

    .hadith-card details { margin-top: 12px; }
    .hadith-card summary { color: #000; font-weight: bold; cursor: pointer; font-size: 12px; }
    .raw-code-box {
        background-color: #262730; color: #ffffff; border: 1px solid #444;
        padding: 15px; border-radius: 8px; font-family: 'Scheherazade New', serif;
        direction: rtl; text-align: right; font-size: 14px; margin-top: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# HJÄLPFUNKTIONER
# ---------------------------------------------------------------------------
def escape_html(text) -> str:
    # "$" escapas så att Streamlit inte tolkar texten som LaTeX
    return html.escape(str(text), quote=False).replace("$", "&#36;")


def clean_for_search(text) -> str:
    """Normaliserar arabisk text: tar bort tashkeel/tatweel, enhetlig alif/ya, enkla mellanslag."""
    if not isinstance(text, str):
        return ""
    text = MARKS_RE.sub("", text)
    text = ALIF_RE.sub("ا", text).replace("ى", "ي")
    return " ".join(text.split())


def compile_highlighter(terms):
    words = sorted({t for t in terms if t}, key=len, reverse=True)  # längst först
    if not words:
        return None
    return re.compile("(" + "|".join(loose_word(w) for w in words) + ")")


def highlight_search_terms(text: str, highlighter) -> str:
    """Markerar sökträffar men rör aldrig HTML-taggar."""
    if highlighter is None:
        return text
    parts = TAG_SPLIT_RE.split(text)  # jämna index = text, udda = taggar/entiteter
    for i in range(0, len(parts), 2):
        parts[i] = highlighter.sub(r'<span class="search-highlight">\1</span>', parts[i])
    return "".join(parts)


def _format_match(m: re.Match) -> str:
    kind, txt = m.lastgroup, m.group(0)
    if kind == "saw":
        return '&nbsp;<span class="saw-symbol">ﷺ</span>'
    if kind == "ra":
        return '&nbsp;<span class="ra-symbol">ؓ</span>'
    if kind == "quote":
        return f"<b>{txt}</b>"
    return f'<span class="{SPAN_CLASSES[kind]}">{txt}</span>'


def apply_original_formatting(original_text) -> str:
    text = str(original_text).replace("\ufffd", "").replace("ـ", "").replace("-", "")
    text = NOISE_RE.sub("", re.sub(r"\s+", " ", text))
    if text.count('"') % 2:
        text += '"'
    formatted = MASTER_PATTERN.sub(_format_match, escape_html(text))
    formatted = re.sub(r"\s+", " ", formatted)
    formatted = re.sub(r"\s+([.،,])", r"\1", formatted)
    return formatted.strip()


def render_card(book: str, number: str, text: str, highlighter) -> str:
    body = highlight_search_terms(apply_original_formatting(text), highlighter)
    raw = "<br>".join(escape_html(line) for line in str(text).splitlines() if line.strip())
    # Allt på en rad: inga tomrader som kan bryta Markdowns HTML-block
    return (
        '<div class="hadith-card">'
        '<div class="card-header">'
        f'<span class="meta-tag">📖 {escape_html(book)}</span>'
        f'<span class="meta-tag"># {escape_html(number)}</span>'
        "</div>"
        f'<div class="arabic-text" lang="ar" dir="rtl">{body}</div>'
        "<details><summary>Original text</summary>"
        f'<div class="raw-code-box">{raw}</div>'
        "</details></div>"
    )


# ---------------------------------------------------------------------------
# DATALOGIK
# ---------------------------------------------------------------------------
def _fetch_book(slug: str, name: str) -> pd.DataFrame:
    retry = Retry(total=3, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504))
    try:
        with requests.Session() as session:
            session.mount("https://", HTTPAdapter(max_retries=retry))
            resp = session.get(API_URL.format(slug=slug), timeout=60)
        resp.raise_for_status()
        hadiths = resp.json().get("hadiths") or []
        if not hadiths:
            raise ValueError("tomt svar")
        df_book = pd.DataFrame(hadiths)[["hadithnumber", "text"]]
    except Exception as exc:
        raise RuntimeError(f"{name}: {exc}") from exc
    df_book["book_name"] = name
    return df_book


# cache_resource returnerar samma objekt utan kopiering (cache_data kopierar hela
# DataFramen vid varje rerun). Misslyckade laddningar cachas inte.
@st.cache_resource(show_spinner=False)
def get_dataset() -> pd.DataFrame:
    with ThreadPoolExecutor(max_workers=len(BOOKS)) as pool:
        frames = list(pool.map(lambda book: _fetch_book(*book), BOOKS))
    full_df = pd.concat(frames, ignore_index=True)
    full_df["hadithnumber"] = full_df["hadithnumber"].astype(str).str.replace(r"\.0$", "", regex=True)
    full_df["search_text"] = full_df["text"].map(clean_for_search)
    return full_df


QUOTE_PAIRS = (('"', '"'), ("«", "»"), ("“", "”"))


def parse_query(raw: str):
    """Returnerar (söktermer, är_fras). En fras i citattecken blir en enda term."""
    q = raw.strip()
    for opening, closing in QUOTE_PAIRS:
        if len(q) >= 2 and q.startswith(opening) and q.endswith(closing):
            phrase = clean_for_search(q[1:-1])
            return ((phrase,) if phrase else ()), True
    return tuple(clean_for_search(q).split()), False


@st.cache_data(show_spinner=False, max_entries=64)
def search_indices(terms: tuple) -> list:
    data = get_dataset()
    mask = pd.Series(True, index=data.index)
    for term in terms:
        mask &= data["search_text"].str.contains(term, regex=False, na=False)
    return data.index[mask].tolist()


# --- Callbacks ---
def toggle_book_filter(book_name: str):
    current = st.session_state.active_book_filter
    st.session_state.active_book_filter = None if current == book_name else book_name
    st.session_state.visible_count = PAGE_SIZE


def show_more():
    st.session_state.visible_count += PAGE_SIZE


# ---------------------------------------------------------------------------
# ANVÄNDARGRÄNSSNITT
# ---------------------------------------------------------------------------
try:
    with st.spinner("Laddar bibliotek (Al-Kutub Al-Sittah)..."):
        df = get_dataset()
except Exception as exc:
    st.error(f"Kunde inte ladda hadith-databasen. Försök igen om en stund.\n\n`{exc}`")
    st.stop()

query = st.text_input(
    "Sök i Al-Kutub Al-Sittah (De sex böckerna):",
    placeholder="مثال: انما الاعمال",
    help='Skriv flera ord för att hitta hadither som innehåller alla. '
    'Sätt citattecken runt för en exakt fras, t.ex. "انما الاعمال بالنيات".',
).strip()

if not query:
    st.info("Vänligen skriv in sökord ovan för att söka i Al-Kutub Al-Sittah.")
    st.stop()

if query != st.session_state.last_query:
    st.session_state.last_query = query
    st.session_state.active_book_filter = None
    st.session_state.visible_count = PAGE_SIZE

terms, is_phrase = parse_query(query)
if not terms:
    st.warning("Du angav tomma citattecken." if is_phrase else "Sökningen innehåller inga sökbara tecken.")
    st.stop()

indices = search_indices(terms)
if not indices:
    st.info("Inga hadither hittades som matchar din sökning.")
    st.stop()

all_results = df.loc[indices]
book_counts = all_results["book_name"].value_counts()

# --- Filterknappar (två kolumner) ---
st.markdown(
    f'<div style="margin-bottom:5px; direction:ltr; font-size:11px;">'
    f"<strong>Hittade {len(all_results):,} träffar. Filtrera:</strong></div>".replace(",", " "),
    unsafe_allow_html=True,
)
cols = st.columns(2, gap="small")
for idx, (book_name, count) in enumerate(book_counts.items()):
    is_active = st.session_state.active_book_filter == book_name
    with cols[idx % 2]:
        st.button(
            f"{book_name} ({count})",
            key=f"btn_{book_name}",
            type="primary" if is_active else "secondary",
            on_click=toggle_book_filter,
            args=(book_name,),
        )

# --- Resultat ---
active_filter = st.session_state.active_book_filter
results = all_results[all_results["book_name"] == active_filter] if active_filter else all_results
visible = st.session_state.visible_count
highlighter = compile_highlighter(terms)

for row in results.iloc[:visible].itertuples():
    st.markdown(
        render_card(row.book_name, row.hadithnumber, row.text, highlighter),
        unsafe_allow_html=True,
    )

remaining = len(results) - visible
if remaining > 0:
    st.button(f"Visa fler ({remaining} kvar)", key="show_more", on_click=show_more)
