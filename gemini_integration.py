# gemini_page_summarizer.py
import os
import sys
import requests
from bs4 import BeautifulSoup, Comment
from datetime import datetime
from google import genai
import textwrap

# Choose one of the allowed URLs
SOURCE_URLS = [
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://www.bbc.com/news/technology",
    "https://edition.cnn.com/business"
]

# pick source by index or pass as CLI arg
def pick_source():
    if len(sys.argv) >= 2:
        u = sys.argv[1].strip()
        if u in SOURCE_URLS:
            return u
        else:
            print("Provided URL not in allowed list, using first URL.")
    return SOURCE_URLS[0]

def fetch_html(url, timeout=20):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PageSummarizer/1.0; +https://example.com/bot)"
    }
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.text

def clean_html(html):
    soup = BeautifulSoup(html, "lxml")

    # remove scripts, styles, noscript, forms, and comments
    for tag in soup(['script', 'style', 'noscript', 'iframe', 'form', 'svg', 'picture', 'source']):
        tag.decompose()
    for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
        comment.extract()

    # remove typical navigation/header/footer elements by tag/class/id heuristics
    removes = []
    selectors = [
        'header', 'nav', 'footer', '.nav', '.navbar', '.breadcrumb',
        '.footer', '.header', '.site-header', '.site-footer', '.advert', '.ads', '[role="navigation"]',
        '.sidebar', '.related', '.promo', '.cookie', '.masthead'
    ]
    for sel in selectors:
        for el in soup.select(sel):
            removes.append(el)
    for r in removes:
        try:
            r.decompose()
        except:
            pass

    # Collect main text: prefer <article>, else <main>, else body paragraphs
    text_blocks = []
    article = soup.find('article')
    if article:
        text_blocks = [p.get_text(separator=" ", strip=True) for p in article.find_all(['p', 'h1','h2','h3','h4','li'])]
    else:
        main = soup.find('main')
        if main:
            text_blocks = [p.get_text(separator=" ", strip=True) for p in main.find_all(['p', 'h1','h2','h3','h4','li'])]
        else:
            # fallback to body paragraphs
            body = soup.body or soup
            text_blocks = [p.get_text(separator=" ", strip=True) for p in body.find_all('p')]

    # filter short/irrelevant items and join
    filtered = [t for t in text_blocks if t and len(t) > 40]
    cleaned = "\n\n".join(filtered)

    # sanitize whitespace
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())
    return cleaned

def build_prompt(source_url, page_title, cleaned_text):
    # custom prompt instructing Gemini to summarize and provide analytical insight
    prompt = textwrap.dedent(f"""
    You are an expert analyst. Given the cleaned webpage content (below), produce:
    1) A concise summary in 4-6 sentences that captures the main points, and
    2) A short analytical insight (2-3 sentences) that goes beyond paraphrase — provide interpretation, implications, or an action-oriented takeaway.
    3) Finally, give a 1-line sentiment or risk note, if applicable.

    Source URL: {source_url}
    Page title: {page_title}

    Cleaned content:
    \"\"\"{cleaned_text[:20000]}\"\"\"

    Output format (JSON):
    {{
      "summary": "<summary text>",
      "analysis": "<analytical insight>",
      "note": "<one-line sentiment or risk note>"
    }}

    Be factual, avoid hallucinations, and base your analysis only on the provided cleaned content.
    """)
    return prompt

def call_gemini(prompt, cleaned_text, model="gemini-2.5-flash", api_key=None):
    if api_key is None:
        api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    client = genai.Client(api_key=api_key)
    # Provide the cleaned content first, then the instruction prompt
    contents = [cleaned_text, prompt]
    # generate content
    resp = client.models.generate_content(model=model, contents=contents)
    # SDK returns resp.text in many examples, otherwise inspect candidates
    text = None
    try:
        text = resp.text
    except Exception:
        pass
    if not text:
        try:
            # attempt to pull candidate text
            text = ""
            for c in resp.candidates:
                # candidate.content may contain parts
                if hasattr(c, "content") and getattr(c.content, "text", None):
                    text += c.content.text
                elif hasattr(c, "text"):
                    text += c.text
        except Exception:
            pass
    return text

def pretty_print_output(url, title, cleaned_len, raw_len, gemini_raw):
    separator = "=" * 80
    print(separator)
    print(f"Source URL : {url}")
    print(f"Page title : {title}")
    print(f"Raw length : {raw_len} chars, Cleaned length : {cleaned_len} chars")
    print(separator)
    print("\nGemini response:\n")
    print(gemini_raw.strip())
    print("\n" + separator + "\n")

def main():
    url = pick_source()
    html = fetch_html(url)
    raw_len = len(html)
    # extract title
    soup = BeautifulSoup(html, "lxml")
    title_tag = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"
    cleaned = clean_html(html)
    cleaned_len = len(cleaned)

    prompt = build_prompt(url, title_tag, cleaned)

    # call gemini
    try:
        gemini_resp = call_gemini(prompt=prompt, cleaned_text=cleaned)
    except Exception as e:
        print("Error calling Gemini API:", e)
        return

    pretty_print_output(url, title_tag, cleaned_len, raw_len, gemini_resp or "<no response>")

if __name__ == "__main__":
    main()
