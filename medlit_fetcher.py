import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="MedLit Fetcher", layout="wide")
st.title("🩺 MedLit Fetcher")
st.markdown("""
Search PubMed and get structured, downloadable article details with direct PDF links via Sci-Hub.
""")

query = st.text_input("🔍 Enter your search term")

if query:
    url = f"https://pubmed.ncbi.nlm.nih.gov/?term={query.replace(' ', '+')}"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")
    articles = soup.select(".docsum-content")

    title_match = []
    others = []

    for article in articles:
        title_elem = article.select_one(".docsum-title")
        if not title_elem:
            continue
        title = title_elem.text.strip()
        link = "https://pubmed.ncbi.nlm.nih.gov" + title_elem["href"]

        # Get PMID
        pmid_match = re.search(r"\d+", title_elem["href"])
        pmid = pmid_match.group(0) if pmid_match else None

        authors = article.select_one(".docsum-authors.full-authors")
        journal = article.select_one(".docsum-journal-citation.full-journal-citation")

        author_text = authors.text.strip() if authors else ""
        journal_text = journal.text.strip() if journal else ""

        # Extract year
        year_match = re.search(r"\b(19|20)\d{2}\b", journal_text)
        pub_year = year_match.group(0) if year_match else ""

        # Vancouver citation
        citation_vancouver = f"{author_text}. {title}. {journal_text}."
        citation_apa = f"{author_text} ({pub_year}). {title}. {journal_text}."
        citation_mla = f"{author_text}. \"{title}.\" {journal_text}, {pub_year}."

        # Sci-Hub PDF link
        scihub_link = f"https://sci-hub.ru/{pmid}" if pmid else ""

        # Fetch references if available
        references_list = []
        if pmid:
            ref_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/citations/"
            ref_res = requests.get(ref_url)
            ref_soup = BeautifulSoup(ref_res.text, "html.parser")
            ref_items = ref_soup.select(".docsum-content")
            for ref in ref_items:
                ref_title_elem = ref.select_one(".docsum-title")
                if ref_title_elem:
                    ref_title = ref_title_elem.text.strip()
                    ref_link = "https://pubmed.ncbi.nlm.nih.gov" + ref_title_elem["href"]
                    references_list.append(f"[{ref_title}]({ref_link})")

        article_info = {
            "title": title,
            "link": link,
            "authors": author_text,
            "journal": journal_text,
            "year": pub_year,
            "citation_vancouver": citation_vancouver,
            "citation_apa": citation_apa,
            "citation_mla": citation_mla,
            "pdf": scihub_link,
            "references_list": references_list
        }

        if query.lower() in title.lower():
            title_match.append(article_info)
        else:
            others.append(article_info)

    col1, col2 = st.columns(2)

    def display_article(article, idx):
        with st.expander(f"{idx+1}. {article['title']}"):
            st.markdown(f"**Authors:** {article['authors']}")
            st.markdown(f"**Journal:** {article['journal']}")
            st.markdown(f"**Publication Year:** {article['year']}")
            with st.popover("📚 View Citation"):
                st.markdown(f"**Vancouver:** {article['citation_vancouver']}")
                st.markdown(f"**APA:** {article['citation_apa']}")
                st.markdown(f"**MLA:** {article['citation_mla']}")
            st.markdown(f"[🔗 PubMed Link]({article['link']})")
            st.markdown(f"[📄 Download PDF]({article['pdf']})")
            if article['references_list']:
                with st.popover("📑 References"):
                    for ref in article['references_list']:
                        st.markdown(f"- {ref}")

    with col1:
        st.subheader("🔍 Articles with Your Keywords in the Title")
        for i, article in enumerate(title_match):
            display_article(article, i)

    with col2:
        st.subheader("📄 Other Relevant Articles")
        for i, article in enumerate(others):
            display_article(article, i)
