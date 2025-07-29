import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re

st.set_page_config(page_title="MedLit Fetcher", layout="wide")
st.title("📚 MedLit Fetcher – PubMed Article Finder")

# User input
query = st.text_input("🔍 Enter your search query:", value="")
max_results = st.slider("Number of articles to display:", 5, 50, 10)
year_range = st.slider("Select publication year range:", 1950, datetime.now().year, (2015, datetime.now().year))

country_filter = st.selectbox("🌍 Filter by region:", ["All", "India", "Foreign"])

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
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
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

    title_tag = article.find("articletitle")
    title = title_tag.text if title_tag else "No Title"

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

    citation = f"{authors_str}. {title}. {journal_title}. {year}. PMID: {pmid}. [PubMed]({pubmed_url})"

    return {
        "title": title,
        "authors": authors_str,
        "journal": journal_title,
        "date": full_date,
        "abstract": abstract_text,
        "citation": citation,
        "pmid": pmid,
        "url": pubmed_url
    }

if st.button("🔎 Search") and query.strip():
    with st.spinner("Fetching articles from PubMed..."):
        ids = fetch_pubmed_articles(query, max_results)
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
