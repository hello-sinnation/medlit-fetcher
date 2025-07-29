import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ------------------------- PAGE SETUP -------------------------
st.set_page_config(page_title="MedLit Fetcher", layout="wide")
st.title("📚 MedLit Fetcher – PubMed Article Finder")

# ---------------------- LIVE MESH SUGGESTIONS ----------------------

def fetch_mesh_suggestions(prefix):
    if not prefix:
        return []
    url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    params = {"label": prefix, "match": "contains", "limit": 10}
    try:
        response = requests.get(url, params=params, timeout=3)
        response.raise_for_status()
        suggestions = [entry["label"] for entry in response.json()]
        return suggestions
    except Exception:
        return []

# Session state for controlled live query
if "search_text" not in st.session_state:
    st.session_state.search_text = ""
if "final_query" not in st.session_state:
    st.session_state.final_query = ""
if "run_search" not in st.session_state:
    st.session_state.run_search = False

# Text input field with on_change callback
def on_text_change():
    st.session_state.final_query = ""
    st.session_state.search_text = st.session_state.temp_input

st.text_input("🔍 Enter your search query:", key="temp_input", on_change=on_text_change)

# Live suggestions display
query = st.session_state.get("search_text", "")
suggestions = fetch_mesh_suggestions(query)

if query and not st.session_state.final_query:
    st.markdown("**💡 Suggestions:**")
    for suggestion in suggestions:
        if st.button(suggestion):
            st.session_state.final_query = suggestion
            st.session_state.search_text = suggestion
            st.session_state.run_search = True
            st.rerun()

# Use selected suggestion or current typed input
active_query = st.session_state.final_query or st.session_state.search_text

# ---------------------- FILTER CONTROLS ----------------------

max_results = st.slider("Number of articles to display:", 5, 50, 10)
year_range = st.slider("Select publication year range:", 1950, datetime.now().year, (2015, datetime.now().year))
country_filter = st.selectbox("🌍 Filter by region:", ["All", "India", "Foreign"])

# ---------------------- PUBMED SEARCH ----------------------

def fetch_pubmed_articles(query, max_results=10):
    country_query = ""
    if country_filter == "India":
        country_query = " AND (India[AD] OR India[PL])"
    elif country_filter == "Foreign":
        country_query = " NOT (India[AD] OR India[PL])"

    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": f'({query}) AND ("{year_range[0]}"[PDAT] : "{year_range[1]}"[PDAT]) AND (humans[MeSH Terms]) AND (journal article[Publication Type]) AND (hasabstract[text]){country_query}',
        "retmode": "json",
        "retmax": max_results,
        "sort": "relevance"
    }
    response = requests.get(base_url, params=params)
    id_list = response.json()["esearchresult"].get("idlist", [])
    return id_list

def fetch_details(pmid):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml"
    }
    response = requests.get(url, params=params)
    soup = BeautifulSoup(response.content, "lxml")
    article = soup.find("pubmedarticle")

    if article is None:
        return {
            "title": "No Title",
            "authors": "N/A",
            "journal": "N/A",
            "date": "N/A",
            "abstract": "No abstract available.",
            "citation": f"PMID: {pmid} (Details not found)",
            "pmid": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        }

    title = article.find("articletitle")
    title_text = title.text if title else "No Title"

    authors = article.find_all("author")
    author_list = []
    for author in authors:
        lastname = author.find("lastname")
        firstname = author.find("forename")
        if lastname and firstname:
            author_list.append(f"{lastname.text} {firstname.text}")
    authors_str = ", ".join(author_list) if author_list else "No authors listed"

    journal = article.find("journal")
    journal_title = journal.find("title").text if journal and journal.find("title") else "Unknown Journal"

    pub_date = journal.find("pubdate") if journal else None
    year = pub_date.find("year").text if pub_date and pub_date.find("year") else ""
    month = pub_date.find("month").text if pub_date and pub_date.find("month") else ""
    day = pub_date.find("day").text if pub_date and pub_date.find("day") else ""
    full_date = f"{day} {month} {year}".strip()

    abstract = article.find("abstract")
    abstract_text = abstract.text.strip() if abstract else "No abstract available."

    pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    citation = f"{authors_str}. {title_text}. {journal_title}. {year}. PMID: {pmid}. [PubMed]({pubmed_url})"

    return {
        "title": title_text,
        "authors": authors_str,
        "journal": journal_title,
        "date": full_date,
        "abstract": abstract_text,
        "citation": citation,
        "pmid": pmid,
        "url": pubmed_url
    }

# ---------------------- SEARCH TRIGGER ----------------------

# Manual or auto-triggered search
if st.button("🔎 Search") or st.session_state.get("run_search", False):
    st.session_state.run_search = False

    if active_query.strip():
        with st.spinner("Fetching articles from PubMed..."):
            ids = fetch_pubmed_articles(active_query, max_results)

            if not ids:
                st.warning("No articles found. Try a different query.")
            else:
                fail_count = 0
                for pmid in ids:
                    data = fetch_details(pmid)
                    if data["title"] == "No Title" and data["authors"] == "N/A":
                        fail_count += 1
                        continue
                    with st.expander(f"📄 {data['title']}"):
                        st.write(f"**Authors:** {data['authors']}")
                        st.write(f"**Journal:** {data['journal']} | **Published:** {data['date']}")
                        st.write(f"**Abstract:** {data['abstract']}")
                        st.markdown(f"📖 **Vancouver Citation:** {data['citation']}", unsafe_allow_html=True)
                        st.markdown("---")
                if fail_count:
                    st.warning(f"{fail_count} articles could not be loaded due to missing data.")
