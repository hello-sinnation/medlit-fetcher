import requests
from bs4 import BeautifulSoup
import streamlit as st
from urllib.parse import quote
import re

# Function to fetch PubMed articles based on a query
def fetch_pubmed_articles(query, max_results=10):
    query_encoded = quote(query)
    url = f"https://pubmed.ncbi.nlm.nih.gov/?term={query_encoded}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    matching_articles = []
    other_articles = []

    for article in soup.find_all("article", class_="full-docsum")[:max_results]:
        title_tag = article.find("a", class_="docsum-title")
        title = title_tag.text.strip() if title_tag else "No title"
        article_link = "https://pubmed.ncbi.nlm.nih.gov" + title_tag['href'] if title_tag else ""

        authors_tag = article.find("span", class_="docsum-authors full-authors")
        authors = authors_tag.text.strip() if authors_tag else "No authors"

        journal_tag = article.find("span", class_="docsum-journal-citation full-journal-citation")
        publication_info = journal_tag.text.strip() if journal_tag else "No publication info"

        pub_date_match = re.search(r"\d{4} [A-Za-z]{3} \d{1,2}|\d{4}", publication_info)
        pub_date = pub_date_match.group() if pub_date_match else "No date"

        journal_name = publication_info.split('.')[0] if publication_info else "No journal"

        vancouver_citation = f"{authors}. {title}. {journal_name}. {pub_date}."

        pdf_url = f"https://sci-hub.se/{article_link}" if article_link else ""

        article_data = {
            "title": title,
            "authors": authors,
            "date": pub_date,
            "journal": journal_name,
            "link": article_link,
            "citation": vancouver_citation,
            "pdf_url": pdf_url
        }

        if all(word.lower() in title.lower() for word in query.split()):
            matching_articles.append(article_data)
        else:
            other_articles.append(article_data)

    return matching_articles, other_articles

# Streamlit app
st.set_page_config(page_title="MedLit Fetcher", layout="wide")
st.title("🧠 MedLit Fetcher: Medical Literature Tool")
st.markdown("""
This app fetches medical research literature from **PubMed** based on your query and displays:
- Title (containing your keywords in a dedicated section)
- Authors
- Publication Date
- Journal Name
- Vancouver-style citation
- PDF download link (via Sci-Hub)
""")

query = st.text_input("Enter your medical search query (e.g., 'laparoscopic cholecystectomy ICG')")
if st.button("Search") and query:
    with st.spinner("Fetching articles from PubMed..."):
        matching, others = fetch_pubmed_articles(query)

        if matching:
            st.markdown("## 🔍 Articles with Your Keywords in the Title")
            for idx, article in enumerate(matching):
                st.markdown(f"### Article {idx+1}")
                st.markdown(f"**Title:** {article['title']}")
                st.markdown(f"**Authors:** {article['authors']}")
                st.markdown(f"**Journal:** {article['journal']}")
                st.markdown(f"**Publication Date:** {article['date']}")
                st.markdown(f"**Citation (Vancouver Style):** {article['citation']}")
                st.markdown(f"[View on PubMed]({article['link']})")
                st.markdown(f"[📄 Download PDF (via Sci-Hub)]({article['pdf_url']})")
                st.markdown("---")
        else:
            st.warning("No results found with your keywords in the title.")

        if others:
            st.markdown("## 📄 Other Relevant Articles")
            for idx, article in enumerate(others):
                st.markdown(f"### Article {idx+1}")
                st.markdown(f"**Title:** {article['title']}")
                st.markdown(f"**Authors:** {article['authors']}")
                st.markdown(f"**Journal:** {article['journal']}")
                st.markdown(f"**Publication Date:** {article['date']}")
                st.markdown(f"**Citation (Vancouver Style):** {article['citation']}")
                st.markdown(f"[View on PubMed]({article['link']})")
                st.markdown(f"[📄 Download PDF (via Sci-Hub)]({article['pdf_url']})")
                st.markdown("---")
