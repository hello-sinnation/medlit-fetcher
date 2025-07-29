import streamlit as st
import requests
from urllib.parse import quote
from time import sleep
import pandas as pd

# Helper function to search PubMed (Entrez API)
def search_pubmed(query, retmax=10):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax
    }
    res = requests.get(base_url, params=params).json()
    id_list = res['esearchresult']['idlist']
    return id_list

# Fetch article details from PubMed

def fetch_pubmed_details(id_list):
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    ids = ",".join(id_list)
    params = {
        "db": "pubmed",
        "id": ids,
        "retmode": "xml"
    }
    res = requests.get(base_url, params=params)
    return res.text

# Use Semantic Scholar API

def search_semantic_scholar(query, limit=10):
    base_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query)}&limit={limit}&fields=title,authors,year,abstract,venue,url,isOpenAccess"
    res = requests.get(base_url)
    return res.json().get("data", [])

# Use CrossRef API

def search_crossref(query, rows=10):
    base_url = f"https://api.crossref.org/works?query={quote(query)}&rows={rows}"
    res = requests.get(base_url)
    return res.json().get("message", {}).get("items", [])

# Display results in a DataFrame and allow export

def build_dataframe(results):
    df = pd.DataFrame(results)
    st.dataframe(df)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "results.csv", "text/csv")

# Streamlit UI

st.set_page_config(page_title="MedLit Fetcher", layout="wide")
st.title("📚 MedLit Fetcher: Research Literature Tool")

query = st.text_input("Enter your research topic or question:", "ICG-guided laparoscopic cholecystectomy")
retmax = st.slider("Number of articles from each database:", 5, 50, 10)

if st.button("Search Literature"):
    with st.spinner("Fetching articles from PubMed..."):
        pubmed_ids = search_pubmed(query, retmax)
        pubmed_results = [f"https://pubmed.ncbi.nlm.nih.gov/{pid}" for pid in pubmed_ids]
        st.subheader("🔬 PubMed Results")
        for link in pubmed_results:
            st.markdown(f"- [PubMed Article]({link})")

    with st.spinner("Fetching articles from Semantic Scholar..."):
        semantic_results = search_semantic_scholar(query, retmax)
        s2_display = []
        for r in semantic_results:
            s2_display.append({
                "Title": r.get("title"),
                "Authors": ", ".join([a['name'] for a in r.get("authors", [])]),
                "Year": r.get("year"),
                "Venue": r.get("venue"),
                "Abstract": r.get("abstract"),
                "Link": r.get("url"),
                "Open Access": r.get("isOpenAccess")
            })
        st.subheader("📘 Semantic Scholar Results")
        build_dataframe(s2_display)

    with st.spinner("Fetching articles from CrossRef..."):
        crossref_results = search_crossref(query, retmax)
        cr_display = []
        for item in crossref_results:
            cr_display.append({
                "Title": item.get("title", [None])[0],
                "Authors": ", ".join([a.get("family", "") for a in item.get("author", [])]) if item.get("author") else None,
                "Year": item.get("issued", {}).get("date-parts", [[None]])[0][0],
                "Journal": item.get("container-title", [None])[0],
                "DOI": item.get("DOI"),
                "Link": item.get("URL")
            })
        st.subheader("📗 CrossRef Results")
        build_dataframe(cr_display)

    st.success("Done fetching articles!")
