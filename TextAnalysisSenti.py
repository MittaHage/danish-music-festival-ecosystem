# Import necessary libraries
import os, re, time, urllib.parse, urllib.request, gzip, json
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import networkx as nx
from networkx.readwrite import json_graph
from networkx.algorithms.community import louvain_communities
from networkx.algorithms.community.quality import modularity
from sklearn.feature_extraction.text import TfidfVectorizer

# Correct import for python-louvain
import community.community_louvain as community_louvain
import zipfile
import io


# -------------------------------------------------------------------
# Raw URL to the zip file
zip_url = "https://raw.githubusercontent.com/MittaHage/danish-music-festival-ecosystem/main/festival_graph_newWiki.zip"

# Download zip into memory
response = urllib.request.urlopen(zip_url).read()

# Open zip from memory
with zipfile.ZipFile(io.BytesIO(response)) as z:
    print("Files inside zip:", z.namelist())  # check contents
    
    # Assuming the JSON file is inside the zip
    with z.open("festival_graph_newWiki.json") as f:
        data = json.load(f)

# Convert to NetworkX graph
G = json_graph.node_link_graph(data)
print("Graph has", G.number_of_nodes(), "nodes and", G.number_of_edges(), "edges")

# -------------------------------------------------------------------
# Louvain communities using NetworkX wrapper
UG = nx.Graph(G)
communities = louvain_communities(UG, seed=0)
M_louvain = modularity(UG, communities)

print(f"Louvain modularity: {M_louvain:.4f}")
print(f"Number of detected communities: {len(communities)}")

# Calculate the sentiment for the 10 largest communities

# Step 1: Select the 7 largest communities - as these are the communities for which we made TF.IDF analysis
sorted_communities = sorted(communities, key=len, reverse=True)
top_communities = sorted_communities[:10]

# Step 2: Calculate average sentiment and list festivals in each community
community_info = []

for i, community in enumerate(top_communities):
    # Get sentiment scores (artists only)
    scores = [G.nodes[n]['sentiment'] for n in community
              if G.nodes[n].get('bipartite') == "artist" and G.nodes[n].get('sentiment') is not None]
    avg_sentiment = sum(scores) / len(scores) if scores else None

    # Get all festivals in the community
    festivals_in_comm = [n for n in community if G.nodes[n].get("bipartite") == "festival_year"]

    # Store info
    community_info.append({
        "index": i,
        "festivals": festivals_in_comm,
        "avg_sentiment": avg_sentiment,
        "size": len(community)
    })

# Step 3: Print community info
print("\n🎼 Community Sentiment Overview (with festivals):")
for info in community_info:
    print(f"Community {info['index'] + 1}:")
    print(f"  Size: {info['size']}")
    print(f"  Festivals: {', '.join(info['festivals']) if info['festivals'] else 'None'}")
    if info['avg_sentiment'] is not None:
        print(f"  Average Sentiment: {info['avg_sentiment']:.3f}")
    else:
        print("  No sentiment data")


# Map node -> community id
comms = sorted(communities, key=len, reverse=True)
cid = {n: i for i, C in enumerate(comms) for n in C}
TOP_K = 10  # highlight top-K communities

# Node sizes based on degree
deg = np.array([UG.degree(n) for n in UG.nodes()], float)
deg = (deg - deg.min()) / (deg.max() - deg.min() + 1e-9)
sizes = 100 + deg * (2000 - 100)

# Layout
pos = nx.forceatlas2_layout(UG, max_iter=500)

# Colors by community
import matplotlib.cm as cm
cmap = cm.get_cmap("tab10", TOP_K)
colors = [cmap(cid[n]) if cid[n] < TOP_K else (0.85, 0.85, 0.85, 0.7) for n in UG.nodes()]

# Separate artists vs festivals
artist_nodes = [n for n in UG.nodes() if UG.nodes[n].get("bipartite") == "artist"]
festival_nodes = [n for n in UG.nodes() if UG.nodes[n].get("bipartite") == "festival_year"]

fig, ax = plt.subplots(figsize=(10, 8))

# Draw edges
nx.draw_networkx_edges(UG, pos, alpha=0.25, width=0.4, ax=ax)

# Draw artists (circles)
nx.draw_networkx_nodes(UG, pos,
                       nodelist=artist_nodes,
                       node_size=[sizes[list(UG.nodes()).index(n)] for n in artist_nodes],
                       node_color=[colors[list(UG.nodes()).index(n)] for n in artist_nodes],
                       node_shape="o", ax=ax)

# Draw festivals (squares)
nx.draw_networkx_nodes(UG, pos,
                       nodelist=festival_nodes,
                       node_size=[sizes[list(UG.nodes()).index(n)] for n in festival_nodes],
                       node_color=[colors[list(UG.nodes()).index(n)] for n in festival_nodes],
                       node_shape="s", ax=ax)

ax.set_title(f"ForceAtlas2 • Louvain Communities • M = {M_louvain:.3f}")
ax.axis("off")
plt.tight_layout()
plt.show()



# ---------- helpers (inline) ----------
def clean(txt):
    if not isinstance(txt, str): return ""
    txt = re.sub(r"\{\{.*?\}\}", " ", txt, flags=re.S)  # remove templates
    txt = re.sub(r"<ref.*?>.*?</ref>", " ", txt, flags=re.S)  # remove refs
    txt = re.sub(r"==.*?==", " ", txt)  # remove section headers
    txt = re.sub(r"\[\[|\]\]|\{|}|==|''+", " ", txt)
    txt = re.sub(r"http\S+", " ", txt)
    txt = re.sub(r"[^a-zA-Z0-9\s]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip().lower()

# ---------- pick top-K  communities ----------
# communities already computed: `communities`
comms_sorted = sorted(communities, key=len, reverse=True)
TOPK_COMMS = 10
top_comm_ids = list(range(min(TOPK_COMMS, len(comms_sorted))))
node2comm = {n: i for i, C in enumerate(comms_sorted) for n in C}

# -------------- Translate the danish nodes --------------
# Loop through all nodes in the graph
for node, data in G.nodes(data=True):
    # Check if node has wikitext and is in Danish
    if data.get("wikitext") and data.get("wiki_language") == "da":
            # Translate to English
        G.nodes[node]["wikitext"] = None            
        print(f"Deleted danish node {node}")  # preview

# -------------- Make wordclouds from the communities --------------

comm_docs  = defaultdict(list)   # comm_id -> [texts...]

for n in G.nodes():
    txt = G.nodes[n].get("wikitext")
    if not txt: 
        continue
    txt = clean(txt)

    # add to community doc (if in top-K)
    cid = node2comm.get(n)
    if cid in top_comm_ids:
        comm_docs[cid].append(txt)

# ---------- concatenate & show sizes ----------
comm_docs  = {cid: " ".join(docs) for cid, docs in comm_docs.items()}

print("\nTop communities and #artists contributing:")
for cid in top_comm_ids:
    print(f"  - community {cid:<2d} : {len(comms_sorted[cid])}")

    # Compute TF–IDF for genres and communities

def show_top_tfidf(docs_dict, title, top_n=10):
    
    print(f"\n🔹 Top TF–IDF words per {title.lower()}")
    print("=" * 60)

    # TF–IDF model
    vectorizer = TfidfVectorizer(
        #stop_words='english', # removes commonly used words with little meaning, such as "the", "are" and "is"
        lowercase=True,
        max_features=5000,
        max_df=0.90,
        token_pattern=r"(?u)\b[a-zA-Z]{2,}\b"
    )

    labels = list(docs_dict.keys())
    texts = [docs_dict[l] for l in labels]
    X = vectorizer.fit_transform(texts)
    terms = vectorizer.get_feature_names_out()

    for i, label in enumerate(labels):
        row = X[i].toarray().flatten()
        top_idx = row.argsort()[-top_n:][::-1]
        top_terms = [(terms[j], round(row[j], 3)) for j in top_idx]
        print(f"\n{title[:-1]} {label}:")
        print("   " + ", ".join([f"{w} ({v})" for w, v in top_terms]))


# --- Run for top 4 communities ---
comm_docs_top10 = {cid: comm_docs[cid] for cid in list(comm_docs.keys())[:4]}
show_top_tfidf(comm_docs_top10, "Communities", top_n=10)



# -------------- Create WordClouds --------------
from wordcloud import WordCloud
import matplotlib.pyplot as plt

def plot_tfidf_wordclouds(docs_dict, title, top_n=100):
    vectorizer = TfidfVectorizer(stop_words='english', lowercase=True, max_features=5000, max_df=0.90, token_pattern=r"(?u)\b[a-zA-Z]{2,}\b")
    labels = list(docs_dict.keys())
    texts = [docs_dict[l] for l in labels]
    X = vectorizer.fit_transform(texts)
    terms = vectorizer.get_feature_names_out()

    fig, axes = plt.subplots(1, 10, figsize=(10 * len(labels), 10))
    if len(labels) == 1: axes = [axes]

    for i, label in enumerate(labels):
        row = X[i].toarray().flatten()
        top_idx = row.argsort()[-top_n:]
        freqs = {terms[j]: row[j] for j in top_idx}
        wc = WordCloud(width=600, height=400, background_color="white").generate_from_frequencies(freqs)
        axes[i].imshow(wc, interpolation="bilinear")
        axes[i].set_title(f"{title[:-1]} {label}", fontsize=12)
        axes[i].axis("off")

    plt.suptitle(f"TF–IDF Word Clouds — {title}", fontsize=14)
    plt.tight_layout()
    plt.show()



# --- Plot for top 4 communities ---
comm_docs_top10 = {cid: comm_docs[cid] for cid in list(comm_docs.keys())[:10]}
plot_tfidf_wordclouds(comm_docs_top10, "Communities")