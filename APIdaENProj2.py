import urllib.request
import urllib.parse
import json
import re
import os
import time
import requests

#%% 

import json
import requests
import networkx as nx

RAW_URL = "https://raw.githubusercontent.com/MittaHage/danish-music-festival-ecosystem/main/festival_network.json"

response = requests.get(RAW_URL, timeout=30)
response.raise_for_status()
data = response.json()

# Build the graph
G = nx.node_link_graph(data)   # converts JSON into a NetworkX graph

# User-Agent for polite requests 
UA = "Mozilla/5.0 (student project)" 
OUTDIR = "Assignment 2 data" 
os.makedirs(OUTDIR, exist_ok=True)


# Helper function to fetch page from a given language wiki
def fetch_page(title, lang="en", _redirect = False):
    baseurl = f"https://{lang}.wikipedia.org/w/api.php?"
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "format": "json"
    }
    try:
        req = urllib.request.Request(baseurl + urllib.parse.urlencode(params), headers={"User-Agent": UA})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
        page = next(iter(data["query"]["pages"].values()))
        if "missing" in page:
            return None
        rev = page["revisions"][0]
        wikitext = rev.get("*") if "*" in rev else rev["slots"]["main"]["*"]

        # Hvis wikitext starter med REDIRECT
        if wikitext.upper().startswith("#REDIRECT") and _redirect is False:
            # Find redirect mål inde i [[...]]
            match = re.search(r"\[\[(.*?)\]\]", wikitext)
            if match:
                redirect_target = match.group(1).strip()
                print(f"➡️ Redirected to: {redirect_target}")
                # Kør fetch_page igen på redirect_target
                return fetch_page(redirect_target.replace(" ", "_").replace("-", "_"), lang=lang, _redirect = True)
            else:
                return None

        # Hvis det er en wiktionary side, spring over
        if wikitext.startswith("{{wiktionary"):
            return None
        if wikitext.startswith("{{Wiktionary"):
            return None
        
        return wikitext
    except Exception as e:
        print(f"⚠️ Error fetching {title} ({lang}): {e}")
        return None

results = []

for node in G.nodes(data=True):
    if node[1].get("bipartite") == "artist":
        artist_id = node[0]   # node ID
        wikitext = None
        lang_used = None

        en_suffixes = ["_(musician)", "_(band)", "_(singer)", "_(American_band)", ""]
        da_suffixes = ["_(musiker)", "_(band)", "_(sanger)", "_(kor)", ""]

        # Try English Wikipedia
        for suffix in en_suffixes:
            if wikitext is None:
                wikitext = fetch_page(artist_id + suffix, lang="en")
                if wikitext:
                    lang_used = "en"

        # Try Danish Wikipedia
        if wikitext is None:
            for suffix in da_suffixes:
                if wikitext is None:
                    wikitext = fetch_page(artist_id + suffix, lang="da")
                    if wikitext:
                        lang_used = "da"

        # Attach as node attribute
        if wikitext:
            G.nodes[artist_id]["wikitext"] = wikitext
            G.nodes[artist_id]["wiki_language"] = lang_used
        else:
            G.nodes[artist_id]["wikitext"] = None
            G.nodes[artist_id]["wiki_language"] = None



#%% 
from afinn import Afinn
import re

afinn_en = Afinn(language='en')
afinn_da = Afinn(language='da')

def tokenize(text):
    if not text:   # catches None or empty string
        return []
    return re.findall(r'\b[a-zæøå]+\b', text.lower())

for node_id, attrs in G.nodes(data=True):
    if attrs.get("bipartite") == "artist":
        text = attrs.get("wikitext", "")
        lang = attrs.get("wiki_language", "en")

        tokens = tokenize(text)

        if lang == "en":
            scores = [afinn_en.score(word) for word in tokens if -1 > afinn_en.score(word) or afinn_en.score(word) > 1]
        elif lang == "da":
            scores = [afinn_da.score(word) for word in tokens if -1 > afinn_en.score(word) or afinn_en.score(word) > 1]
        else:
            scores = []

        if scores:
            # Normalize from -5…+5 to 0…10
            normalized_scores = [(s + 5) for s in scores]
            sentiment_value = sum(normalized_scores) / len(normalized_scores)
        else:
            sentiment_value = None

        # Attach sentiment as a node attribute
        G.nodes[node_id]["sentiment"] = sentiment_value


import networkx as nx
import json

# Convert graph to node-link dictionary
graph_dict = nx.node_link_data(G)

# Choose a specific path on your computer
save_path = r"C:\Users\KarolineHeleneBaarsø\Desktop\11 - semester\Social Graphs\festival_graph.json"

# Save dictionary as JSON file
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(graph_dict, f, ensure_ascii=False, indent=2)

print(f"Graph saved as JSON at {save_path}")