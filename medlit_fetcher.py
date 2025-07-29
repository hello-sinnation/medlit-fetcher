import streamlit as st
import requests
from bs4 import BeautifulSoup
from scholarly import scholarly
from typing import List, Dict
import re
import base64

st.set_page_config(page_title="MedLit Fetcher", layout="wide")

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

if st.toggle("🌗 Dark Mode", value=st.session_state.dark_mode):
    st.session_state.dark_mode = True
    st.markdown("""
        <style>
        body { background-color: #1e1e1e; color: white; }
        .stButton>button { background-color: #333; color: white; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.session_state.dark_mode = False

st.markdown("""
    <style>
    .article-section {padding: 10px; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 10px;}
    .section-header {font-size: 20px; font-weight: bold; margin-top: 20px;}
    .icon-button {margin-left: 10px; cursor: pointer;}
    </style>
""", unsafe_allow_html=True)

bookmarked_articles = st.session_state.get("bookmarks", [])

def fetch_pubmed_articles(term: str, max_articles: int = 10) -> List[Dict]:
    url = f"https://pubmed.ncbi.nlm.nih.gov/?term={term.replace(' ', '+')}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    for i, item in enumerate(soup.select('.docsum-content')[:max_articles]):
        title_tag = item.find('a', class_='docsum-title')
        if not title_tag:
            continue
        title = title_tag.text.strip()
        link = 'https://pubmed.ncbi.nlm.nih.gov' + title_tag['href']
        details = item.find('span', class_='docsum-journal-citation full-journal-citation')
        authors_tag = item.find('span', class_='docsum-authors full-authors')
        authors = authors_tag.text.strip() if authors_tag else "Not Available"
        date = details.text.strip().split('.')[0] if details else "Unknown"
        type_tag = item.find('span', class_='publication-type')
        article_type = type_tag.text.strip() if type_tag else "Article"
        abstract_tag = item.find('div', class_='full-view-snippet')
        abstract = abstract_tag.text.strip() if abstract_tag else "Abstract not available."
        journal = details.text.strip() if details else ""
        citation = f"{authors}. {title}. {journal}. {date}. {link}"
        articles.append({
            'title': title,
            'link': link,
            'authors': authors,
            'journal': journal,
            'date': date,
            'citation': citation,
            'type': article_type,
            'abstract': abstract
        })
    return articles

def fetch_scihub_pdf_link(pubmed_url: str) -> str:
    try:
        sci_hub_url = f"https://sci-hub.se/{pubmed_url}"
        r = requests.get(sci_hub_url)
        soup = BeautifulSoup(r.content, 'html.parser')
        iframe = soup.find('iframe')
        if iframe and 'src' in iframe.attrs:
            src = iframe['src']
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://sci-hub.se' + src
            return src
    except:
        pass
    return ""

def fetch_references(pubmed_url: str) -> List[Dict]:
    try:
        response = requests.get(pubmed_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        ref_section = soup.find('section', {'id': 'references'})
        if not ref_section:
            return []
        references = []
        for ref in ref_section.find_all('li'):
            title = ref.text.strip().split('.')[0]
            link_tag = ref.find('a', href=True)
            link = 'https://pubmed.ncbi.nlm.nih.gov' + link_tag['href'] if link_tag else pubmed_url
            references.append({'title': title, 'link': link})
        return references
    except:
        return []

def show_articles(articles: List[Dict], header: str):
    st.markdown(f"<div class='section-header'>{header} ({len(articles)} results)</div>", unsafe_allow_html=True)
    for i, article in enumerate(articles):
        with st.expander(f"{i+1}. {article['title']}"):
            st.markdown(f"**Authors:** {article['authors']}")
            st.markdown(f"**Journal:** {article['journal']}")
            st.markdown(f"**Publication Year:** {article['date']}")
            st.markdown(f"**Type:** {article['type']}")
            st.markdown(f"**Abstract:** {article['abstract']}")

            cols = st.columns([1, 1, 1, 1, 1])
            with cols[0]:
                if st.button("📄 View Citation", key=f"cite_{header}_{i}"):
                    st.code(article['citation'], language='text')
            with cols[1]:
                st.markdown(f"[🔗 PubMed Link]({article['link']})")
            with cols[2]:
                pdf_link = fetch_scihub_pdf_link(article['link'])
                if pdf_link:
                    st.markdown(f"[📥 Download PDF]({pdf_link})")
                else:
                    st.write("🔒 PDF not found")
            with cols[3]:
                if st.button("📚 References", key=f"refs_{header}_{i}"):
                    st.info("Loading references...")
                    refs = fetch_references(article['link'])
                    if refs:
                        for j, ref in enumerate(refs):
                            st.markdown(f"{j+1}. [{ref['title']}]({ref['link']})")
                    else:
                        st.warning("No references found")
            with cols[4]:
                if st.button("🔖 Bookmark", key=f"bm_{header}_{i}"):
                    st.session_state.bookmarks = st.session_state.get("bookmarks", []) + [article]
                    st.success("Bookmarked!")

st.title("🩺 MedLit Fetcher")
st.markdown("""
Search PubMed and get structured, downloadable article details with direct PDF links via Sci-Hub.
""")

search_term = st.text_input("🔍 Enter your search term")
max_articles = st.slider("📊 Number of articles to display", 5, 100, 10)

if search_term:
    articles = fetch_pubmed_articles(search_term, max_articles=max_articles)
    title_matched = [a for a in articles if re.search(search_term, a['title'], re.IGNORECASE)]
    others = [a for a in articles if a not in title_matched]

    year_filter = st.multiselect("📅 Filter by Year", sorted(set(a['date'] for a in articles)))
    journal_filter = st.multiselect("📰 Filter by Journal", sorted(set(a['journal'] for a in articles)))

    if year_filter:
        title_matched = [a for a in title_matched if a['date'] in year_filter]
        others = [a for a in others if a['date'] in year_filter]
    if journal_filter:
        title_matched = [a for a in title_matched if a['journal'] in journal_filter]
        others = [a for a in others if a['journal'] in journal_filter]

    col1, col2 = st.columns(2)
    with col1:
        show_articles(title_matched, "📘 Articles with Your Keywords in the Title")
    with col2:
        show_articles(others, "📙 Other Relevant Articles")

    if st.session_state.get("bookmarks"):
        st.markdown("## 🔖 Bookmarked Articles")
        show_articles(st.session_state["bookmarks"], "🔖 Bookmarks")
