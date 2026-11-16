import os
import json
import random
import itertools
import datetime
from xml.sax.saxutils import escape
from google import genai
from google.genai import types

# --- CONFIGURATION ---
GITHUB_USERNAME = "Randa-Rawashdeh"  # <-- REPLACE WITH YOUR GITHUB USERNAME
REPO_NAME = "ai-compare-hub"
BASE_URL = f"https://{GITHUB_USERNAME}.github.io/{REPO_NAME}"
MODEL_ID = "gemini-2.5-flash"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")


def load_products(filepath="products.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_existing_pages():
    return {
        f for f in os.listdir(".")
        if f.endswith(".html") and f != "index.html"
    }


def pick_new_pair(products, existing_files):
    same_cat_pairs = []
    cross_cat_pairs = []

    for p1, p2 in itertools.combinations(products, 2):
        s1, s2 = slugify(p1["name"]), slugify(p2["name"])
        f_forward = f"{s1}-vs-{s2}.html"
        f_reverse = f"{s2}-vs-{s1}.html"

        if f_forward not in existing_files and f_reverse not in existing_files:
            if p1["category"] == p2["category"]:
                same_cat_pairs.append((p1, p2))
            else:
                cross_cat_pairs.append((p1, p2))

    # Prioritize same-category comparisons for higher search intent
    if same_cat_pairs:
        return random.choice(same_cat_pairs)
    if cross_cat_pairs:
        return random.choice(cross_cat_pairs)
    return None, None


def generate_comparison_data(p1, p2):
    prompt = f"""
Compare {p1['name']} and {p2['name']} for a buyer deciding between them in 2026.

Tool 1: {p1['name']} | Category: {p1['category']} | Price: {p1['price']} | Best For: {p1['best_for']} | Key Feature: {p1['key_feature']}
Tool 2: {p2['name']} | Category: {p2['category']} | Price: {p2['price']} | Best For: {p2['best_for']} | Key Feature: {p2['key_feature']}

Return a strictly valid JSON object with these exact keys:
- "meta_description": SEO meta description under 155 characters
- "pinterest_description": Engaging 2-sentence summary with 4 hashtags for Pinterest auto-posting
- "quick_verdict": 2-3 sentence executive summary stating clearly when to choose {p1['name']} vs {p2['name']}
- "comparison_rows": list of 4 objects, each with "feature", "tool1_value", "tool2_value" (covering Pricing, Best For, Standout Strength, and Limitations)
- "tool1_pros": list of 3 concise bullet strings
- "tool1_cons": list of 2 concise bullet strings
- "tool2_pros": list of 3 concise bullet strings
- "tool2_cons": list of 2 concise bullet strings
- "faqs": list of 3 objects, each with "question" and "answer"
"""
    response = client.models.generate_content(
        model=MODEL_ID,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )
    return json.loads(response.text)


def render_comparison_html(p1, p2, data, filename):
    title = f"{p1['name']} vs {p2['name']} (2026): Pricing, Features & Verdict"
    canonical = f"{BASE_URL}/{filename}"

    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": faq["question"],
                "acceptedAnswer": {"@type": "Answer", "text": faq["answer"]},
            }
            for faq in data["faqs"]
        ],
    }

    rows_html = "\n".join(
        f"<tr><td><strong>{escape(r['feature'])}</strong></td>"
        f"<td>{escape(r['tool1_value'])}</td>"
        f"<td>{escape(r['tool2_value'])}</td></tr>"
        for r in data["comparison_rows"]
    )

    p1_pros = "".join(f"<li>{escape(x)}</li>" for x in data["tool1_pros"])
    p1_cons = "".join(f"<li>{escape(x)}</li>" for x in data["tool1_cons"])
    p2_pros = "".join(f"<li>{escape(x)}</li>" for x in data["tool2_pros"])
    p2_cons = "".join(f"<li>{escape(x)}</li>" for x in data["tool2_cons"])
    faqs_html = "".join(
        f"<div class='faq-item'><h3>{escape(f['question'])}</h3><p>{escape(f['answer'])}</p></div>"
        for f in data["faqs"]
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(data['meta_description'])}">
  <link rel="canonical" href="{canonical}">
  <script type="application/ld+json">{json.dumps(faq_schema)}</script>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 820px; margin: 0 auto; padding: 24px; line-height: 1.65; color: #1e293b; background: #f8fafc; }}
    .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 28px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
    h1 {{ font-size: 1.9rem; color: #0f172a; margin-top: 8px; }}
    h2 {{ font-size: 1.35rem; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; }}
    .verdict {{ background: #eff6ff; border-left: 4px solid #2563eb; padding: 18px; border-radius: 8px; margin: 20px 0; }}
    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
    th, td {{ border: 1px solid #e2e8f0; padding: 12px 14px; text-align: left; }}
    th {{ background: #f1f5f9; font-weight: 600; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    @media (max-width: 640px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    .cta-box {{ display: flex; gap: 14px; flex-wrap: wrap; margin: 24px 0; }}
    .btn {{ flex: 1; min-width: 200px; text-align: center; background: #2563eb; color: #fff; font-weight: 600; padding: 14px 20px; border-radius: 8px; text-decoration: none; }}
    .btn.secondary {{ background: #0f172a; }}
    .disclosure {{ font-size: 0.8rem; color: #64748b; margin-top: 32px; }}
  </style>
</head>
<body>
  <p><a href="index.html">&larr; All AI Tool Comparisons</a></p>
  <div class="card">
    <h1>{escape(title)}</h1>
    <div class="verdict"><strong>Quick Verdict:</strong> {escape(data['quick_verdict'])}</div>
    <div class="cta-box">
      <a class="btn" href="{escape(p1['affiliate_url'])}" rel="nofollow sponsored noopener" target="_blank">Try {escape(p1['name'])} ({escape(p1['price'])}) &rarr;</a>
      <a class="btn secondary" href="{escape(p2['affiliate_url'])}" rel="nofollow sponsored noopener" target="_blank">Try {escape(p2['name'])} ({escape(p2['price'])}) &rarr;</a>
    </div>
    <h2>Side-by-Side Comparison</h2>
    <table>
      <thead><tr><th>Feature</th><th>{escape(p1['name'])}</th><th>{escape(p2['name'])}</th></tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    <div class="grid">
      <div>
        <h2>{escape(p1['name'])} Pros &amp; Cons</h2>
        <strong>Pros</strong><ul>{p1_pros}</ul>
        <strong>Cons</strong><ul>{p1_cons}</ul>
      </div>
      <div>
        <h2>{escape(p2['name'])} Pros &amp; Cons</h2>
        <strong>Pros</strong><ul>{p2_pros}</ul>
        <strong>Cons</strong><ul>{p2_cons}</ul>
      </div>
    </div>
    <h2>Frequently Asked Questions</h2>
    {faqs_html}
    <div class="cta-box">
      <a class="btn" href="{escape(p1['affiliate_url'])}" rel="nofollow sponsored noopener" target="_blank">Get Started with {escape(p1['name'])} &rarr;</a>
      <a class="btn secondary" href="{escape(p2['affiliate_url'])}" rel="nofollow sponsored noopener" target="_blank">Get Started with {escape(p2['name'])} &rarr;</a>
    </div>
    <p class="disclosure">Affiliate Disclosure: This comparison is independently generated. If you purchase through links on this page, we may earn an affiliate commission at no extra cost to you.</p>
  </div>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)


def update_metadata_and_feeds(new_entry=None):
    meta_file = "published_meta.json"
    if os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            entries = json.load(f)
    else:
        entries = []

    if new_entry:
        entries.insert(0, new_entry)
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)

    # Build clean responsive index.html
    cards_html = "\n".join(
        f"""<a class="item" href="{escape(e['filename'])}">
          <span class="badge">{escape(e['category'])}</span>
          <h2>{escape(e['title'])}</h2>
          <p>{escape(e['summary'])}</p>
        </a>"""
        for e in entries
    )

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Software &amp; SaaS Comparisons (2026)</title>
  <link rel="alternate" type="application/rss+xml" title="AI Comparisons RSS" href="{BASE_URL}/feed.xml">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 960px; margin: 0 auto; padding: 32px 20px; background: #f8fafc; color: #0f172a; }}
    header {{ text-align: center; margin-bottom: 36px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 18px; }}
    .item {{ display: block; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; text-decoration: none; color: inherit; transition: transform 0.15s; }}
    .item:hover {{ transform: translateY(-2px); border-color: #2563eb; }}
    .badge {{ font-size: 0.75rem; background: #eff6ff; color: #2563eb; padding: 3px 8px; border-radius: 99px; font-weight: 600; }}
    h2 {{ font-size: 1.1rem; margin: 10px 0 8px; }}
    p {{ font-size: 0.9rem; color: #475569; margin: 0; }}
  </style>
</head>
<body>
  <header>
    <h1>AI Tool &amp; SaaS Comparisons</h1>
    <p>Side-by-side pricing, features, and buying verdicts updated daily.</p>
  </header>
  <div class="grid">{cards_html}</div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(index_html)

    # Build RSS 2.0 feed.xml (15 newest items for Make.com -> Pinterest)
    rss_items = "\n".join(
        f"""<item>
      <title>{escape(e['title'])}</title>
      <link>{BASE_URL}/{escape(e['filename'])}</link>
      <guid>{BASE_URL}/{escape(e['filename'])}</guid>
      <pubDate>{escape(e['pub_date'])}</pubDate>
      <description>{escape(e['pinterest_description'])}</description>
    </item>"""
        for e in entries[:15]
    )

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>AI Tool &amp; SaaS Comparisons</title>
    <link>{BASE_URL}/</link>
    <description>Daily AI software side-by-side reviews and comparisons</description>
    {rss_items}
  </channel>
</rss>"""

    with open("feed.xml", "w", encoding="utf-8") as f:
        f.write(rss_xml)


def main():
    products = load_products()
    existing = get_existing_pages()
    p1, p2 = pick_new_pair(products, existing)

    if not p1:
        print("All product combinations have already been generated!")
        update_metadata_and_feeds()
        return

    filename = f"{slugify(p1['name'])}-vs-{slugify(p2['name'])}.html"
    print(f"Generating {filename}...")

    data = generate_comparison_data(p1, p2)
    render_comparison_html(p1, p2, data, filename)

    pub_date = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    new_entry = {
        "filename": filename,
        "title": f"{p1['name']} vs {p2['name']} (2026)",
        "category": p1["category"],
        "summary": data["meta_description"],
        "pinterest_description": data["pinterest_description"],
        "pub_date": pub_date,
    }
    update_metadata_and_feeds(new_entry)
    print(f"Published {filename} successfully.")


if __name__ == "__main__":
    main()
                  
