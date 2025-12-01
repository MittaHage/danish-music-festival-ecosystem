import urllib.request
import urllib.parse
import json
import re
import os
import time

# User-Agent for polite requests
UA = "Mozilla/5.0 (student project)"
OUTDIR = "Assignment 2 data"
os.makedirs(OUTDIR, exist_ok=True)

# Raw artist list (shortened here for readability, keep your full list)
artistRawList = [
    ('roskilde-festival-1971', 'tom-bailey'), ('roskilde-festival-1971', 'surprise'), ('roskilde-festival-1971', 'per-kofoed'), ('roskilde-festival-1971', 'phillias-fogg'), ('roskilde-festival-1971', 'dr-dopojam'), ('roskilde-festival-1971', 'vannis-aften'), ('roskilde-festival-1971', 'sunny-side-stompers'), ('roskilde-festival-1971', 'gasolin'), ('roskilde-festival-1971', 'midnight-sun'), ('roskilde-festival-1971', 'strawbs'), ('roskilde-festival-1971', 'povl-dissing'), ('roskilde-festival-1971', 'papa-bues-jazzband'), ('roskilde-festival-1971', 'stefan-grossman'), ('roskilde-festival-1971', 'stefan-grossmand'), ('roskilde-festival-1971', 'sebastian-band'), ('roskilde-festival-1971', 'c-sar'), ('roskilde-festival-1971', 'burnin-red-ivanhoe'), ('roskilde-festival-1971', 'andrew-john'), ('roskilde-festival-1971', 'alex-campbell'), ('roskilde-festival-1971', 'lousiana-hot-seven'), ('roskilde-festival-1971', 'spider-john-koerner'), ('roskilde-festival-1971', 'fessors-big-city-band'), ('roskilde-festival-1971', 'alrune-rod'), ('roskilde-festival-1971', 'per-dich'), ('roskilde-festival-1971', 'delta-blues-band'), ('roskilde-festival-1971', 'no-name-requested'), ('roskilde-festival-1971', 'day-of-phoenix'), ('roskilde-festival-1971', 'mick-softley'), ('roskilde-festival-1971', 'klosterband'), ('roskilde-festival-1971', 'engine'), ('roskilde-festival-1971', 'grease-band'), ('roskilde-festival-1971', 'fujara'), ('roskilde-festival-1971', 'skin-alley'), ('roskilde-festival-1972', 'kinks'), ('roskilde-festival-1972', 'the-kinks'), ('roskilde-festival-1972', 'andr-williams'), ('roskilde-festival-1972', 'vannis-aften'), ('roskilde-festival-1972', 'purple-door-gang'), ('roskilde-festival-1972', 'arman-sumpe'), ('roskilde-festival-1972', 'paddy-doyles'), ('roskilde-festival-1972', 'dr-dopojam'), ('roskilde-festival-1972', 'gasolin'), ('roskilde-festival-1972', 'gnags'), ('roskilde-festival-1972', 'sha-na-na'), ('roskilde-festival-1972', 'midnight-sun'), ('roskilde-festival-1972', 'smile'), ('roskilde-festival-1972', 'family'), ('roskilde-festival-1972', 'book'), ('roskilde-festival-1972', 'contact'), ('roskilde-festival-1972', 'andrew-john'), ('roskilde-festival-1972', 'alex-campbell'), ('roskilde-festival-1972', 'starfuckers'), ('roskilde-festival-1972', 'david-blue'), ('roskilde-festival-1972', 'saft'), ('roskilde-festival-1972', 'fessors-big-city-band'), ('roskilde-festival-1972', 'alrune-rod'), ('roskilde-festival-1972', 'amon-d-l'), ('roskilde-festival-1972', 'delta-blues-band'), ('roskilde-festival-1972', 'tony-busch'), ('roskilde-festival-1972', 'bork'), ('roskilde-festival-1972', 'day-break'), ('roskilde-festival-1972', 'horst'), ('roskilde-festival-1972', 'hurdy-gurdy'), ('roskilde-festival-1972', 'musikpatruljen'), ('roskilde-festival-1972', 'polyfeen'), ('roskilde-festival-1972', 'fujara'), ('roskilde-festival-1973', 'canned-heat'), ('roskilde-festival-1973', 'negro-spiritual-elim-s-kor'), ('roskilde-festival-1973', 'ewald-thomsen-spillem-nd'), ('roskilde-festival-1973', 'fairport-convention'), ('roskilde-festival-1973', 'kerne'), ('roskilde-festival-1973', 'sh-kmannslaget'), ('roskilde-festival-1973', 'dr-dopojam'), ('roskilde-festival-1973', 'den-gamle-mand-og-havet'), ('roskilde-festival-1973', 'sensory-system'), ('roskilde-festival-1973', 'gasolin'), ('roskilde-festival-1973', 'midnight-sun'), ('roskilde-festival-1973', 'v8'), ('roskilde-festival-1973', 'strawbs'), ('roskilde-festival-1973', 'burnin-red-ivanhoe'), ('roskilde-festival-1973', 'olsen'), ('roskilde-festival-1973', 'culpeppers-orchard'), ('roskilde-festival-1973', 'culpepper-s-orchard'), ('roskilde-festival-1973', 'fessors-big-city-band'), ('roskilde-festival-1973', 'alrune-rod'), ('roskilde-festival-1973', 'kansas-city-stompers'), ('roskilde-festival-1973', 'hair')
]

# Build dictionary: festival → list of cleaned artists
festival_dict = {}
for festival, artist in artistRawList:
    artist_clean = artist.replace(" ", "_").replace("-", "_").title()
    festival_dict.setdefault(festival, []).append(artist_clean)

print(f"Festivals processed: {len(festival_dict)}")
for fest, artists in festival_dict.items():
    print(f"{fest}: {len(artists)} artists")

# Helper function to fetch page from a given language wiki
def fetch_page(title, lang="en"):
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
        if wikitext.upper().startswith("#REDIRECT"):
            # Find redirect mål inde i [[...]]
            match = re.search(r"\[\[(.*?)\]\]", wikitext)
            if match:
                redirect_target = match.group(1).strip()
                print(f"➡️ Redirected to: {redirect_target}")
                # Kør fetch_page igen på redirect_target
                return fetch_page(redirect_target.replace(" ", "_").replace("-", "_"), lang=lang)
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

saved_files = []

# Iterate over festivals and artists
for festival, artists in festival_dict.items():
    print(f"\n🎶 Processing festival: {festival}")
    for i, artist in enumerate(artists, 1):
        wikitext = None

        # Definer suffix-lister inkl. symboler
        en_suffixes = ["_(musician)", "_(band)", "_(singer)","_(American_band)",""]
        da_suffixes = ["_(musiker)", "_(band)","_(sanger)",""]

        # Prøv engelsk Wikipedia først
        for suffix in en_suffixes:
            if wikitext is None:
                wikitext = fetch_page(artist + suffix, lang="en")

        # Hvis stadig ikke fundet, prøv dansk Wikipedia
        if wikitext is None:
            for suffix in da_suffixes:
                if wikitext is None:
                    wikitext = fetch_page(artist + suffix, lang="da")

        if wikitext is None:
            print(f"⚠️ Skipped {artist}: no page found in EN or DA")
            continue

        # Gem til computer
        safe_filename = re.sub(r'[\\/*?:"<>|]', "_", artist)
        filepath = os.path.join(OUTDIR, safe_filename + ".txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(wikitext)

        saved_files.append(filepath)
        if i % 10 == 0:
            print(f"Saved {i}/{len(artists)} pages")
        time.sleep(0.05)

print(f"\n✅ Total files saved: {len(saved_files)} → folder '{OUTDIR}'")
