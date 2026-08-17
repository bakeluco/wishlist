#!/usr/bin/env python3
"""
Reads list_of_games.txt and writes index.html — a visual gallery with Steam cover art.

HOW TO RUN:
1) Create a virtual environment:
    python3 -m venv venv
2) Activate the virtual environment:
    source venv/bin/activate
3) Install your packages inside the virtual environment:
    pip install ....

REGENERATE AFTER ANY EDIT
--------------------------
    python3 gen_games.py

Commit both list_of_games.txt and index.html to GitHub.
GitHub Pages will serve index.html automatically.
Tip: rename index.html → index.html in your repo so the root URL opens it directly.


HOW list_of_games.txt WORKS
============================

CATEGORIES
----------
Wrap a name in dashes on its own line. Everything below belongs to that
category until the next header.

    -SOULS-LIKE-
    https://store.steampowered.com/app/1245620/ELDEN_RING/
    https://store.steampowered.com/app/1627720/Lies_of_P/

ADD A STEAM GAME
----------------
Paste the Steam store URL on its own line under the right category.
The title is read from the URL slug automatically — no need to type it.

    https://store.steampowered.com/app/1245620/ELDEN_RING/

Works the same for GOG, Epic, and itch.io URLs.
For itch.io you can optionally write a title before the URL:

    Pathogen-X https://sodaraptor.itch.io/pathogen-x

ADD / CHANGE A BADGE
---------------------
Append recognised words anywhere on the same line (case-insensitive).
Parentheses are optional but keep things tidy.

    https://store.steampowered.com/app/1245620/ELDEN_RING/ (owned)
    https://store.steampowered.com/app/2358720/Black_Myth_Wukong/ (denuvo - cracked)

Recognised badge words:
    owned   → green  — you own it
    played  → blue   — you've finished / played it
    denuvo  → red    — has Denuvo DRM
    cracked → orange — Denuvo gone / cracked

MARK A GAME AS PLAYED (typical workflow)
-----------------------------------------
Find the line in list_of_games.txt, add "(played)" at the end, save, regenerate.

    Before: https://store.steampowered.com/app/1245620/ELDEN_RING/
    After:  https://store.steampowered.com/app/1245620/ELDEN_RING/ (played)

ADD A GAME WITHOUT A LINK YET
------------------------------
Just write the title as plain text. It will show a "no link" badge and a
letter placeholder instead of cover art. Replace it with the URL later.

    -SOULS-LIKE-
    Some Cool Upcoming Game

DELETE A GAME
-------------
Delete its line from list_of_games.txt. Then regenerate.

ADD A NEW CATEGORY
------------------
Add a header line (dashes required):

    -RHYTHM GAMES-
    https://store.steampowered.com/app/...
  
===============
Your workflow from now on:

Edit list_of_games.txt — add/remove/badge games
Run python3 gen_games.py — regenerates index.html
git add list_of_games.txt index.html && git commit && git push
For GitHub Pages: go to your repo's Settings → Pages → set source to the main branch root. 
Rename index.html to index.html in the repo if you want username.github.io/reponame to open it directly without a /index.html suffix.

Common edits in list_of_games.txt:

Beat a game → append (played) to its line
Bought a game → append (owned) to its line
Add a new game → paste the Steam URL under the right -CATEGORY- header
Remove a game → delete the line
Add a game you can't find yet → just write its name as plain text


HOW manga.txt WORKS
====================
One MyAnimeList manga URL per line (an optional leading index/tab is ignored):

    https://myanimelist.net/manga/85781/Dungeon_Meshi

Title, cover image, volumes/chapters, status, genres, themes, demographic,
serialization and authors are scraped from the MAL page the first time a
manga is seen, then cached in manga_cache.json so re-running the script
doesn't hit MAL again. Delete an entry from that cache (or pass
--refresh-manga to re-fetch everything) to pick up changes on MAL, e.g. a
series moving from "Publishing" to "Finished".
"""

import re, json, os, sys, time, html as html_lib, urllib.request, urllib.error

INPUT  = os.path.join(os.path.dirname(__file__), 'list_of_games.txt')
OUTPUT = os.path.join(os.path.dirname(__file__), 'index.html')

MANGA_INPUT = os.path.join(os.path.dirname(__file__), 'manga.txt')
MANGA_CACHE = os.path.join(os.path.dirname(__file__), 'manga_cache.json')
MAL_URL_RE  = re.compile(r'myanimelist\.net/manga/(\d+)(?:/([^/?\s]*))?')

def parse_badges(s):
    b, l = [], s.lower()
    if 'owned'  in l: b.append('owned')
    if re.search(r'\bplayed\b', l): b.append('played')
    if 'denuvo' in l and 'cracked' in l: b += ['denuvo','cracked']
    elif 'denuvo' in l: b.append('denuvo')
    elif 'cracked' in l: b.append('cracked')
    return list(dict.fromkeys(b))

def slug2title(slug):
    return re.sub(r'\s+', ' ', slug.replace('_',' ').replace('-',' ')).strip()

def parse():
    G, cat = {}, None

    def merge(k, e):
        if k in G:
            for c in e['categories']:
                if c not in G[k]['categories']: G[k]['categories'].append(c)
            for b in e['badges']:
                if b not in G[k]['badges']:     G[k]['badges'].append(b)
        else:
            G[k] = e

    def add(k, title, url, tp, cats, badges, img=None):
        merge(k, {'title':title, 'url':url, 'type':tp,
                  'categories':list(cats), 'badges':list(badges), 'image':img})

    with open(INPUT, encoding='utf-8') as f:
        lines = f.readlines()

    for raw in lines:
        s = raw.strip()
        if not s: continue

        # Category header: "-- DENUVO --", "-CRPG-", "- METROIDVANIA- ", etc.
        m = re.match(r'^[-\s]*-+\s*(.+?)\s*-+\s*$', s)
        if m: cat = m.group(1).strip(); continue
        if re.match(r'^\s*STEAM\s*$', s, re.I): continue
        if re.match(r'^\s*ITCH\s*$',  s, re.I): cat = 'Itch.io'; continue

        badges = parse_badges(s)
        if cat and 'DENUVO' in cat.upper() and 'denuvo' not in badges:
            badges.append('denuvo')
        cats = [cat] if cat else ['Other']

        # Steam (may have multiple on one line)
        steam = re.findall(r'https://store\.steampowered\.com/app/(\d+)/([^/\s]*)', s)
        if steam:
            for aid, slug in steam:
                t = slug2title(slug) if slug else f'Game {aid}'
                add(aid, t, f'https://store.steampowered.com/app/{aid}/', 'steam', cats, badges,
                    f'https://cdn.cloudflare.steamstatic.com/steam/apps/{aid}/header.jpg')
            continue

        # GOG
        m = re.search(r'https://www\.gog\.com/\S+', s)
        if m:
            url = m.group(0).rstrip(')')
            add(url, slug2title(url.split('/')[-1]), url, 'gog', cats, badges)
            continue

        # Epic
        m = re.search(r'https://store\.epicgames\.com/\S+', s)
        if m:
            url = m.group(0).rstrip(')')
            add(url, slug2title(url.split('/')[-1]), url, 'epic', cats, badges)
            continue

        # Itch.io
        itches = re.findall(r'https://[^.\s]+\.itch\.io/[^\s]+', s)
        if itches:
            for iu in itches:
                url   = re.sub(r'\.{2,}$', '', iu).rstrip('.')
                title = slug2title(url.split('/')[-1])
                before = s[:s.find(iu)].strip().rstrip(' -')
                if before and not before.startswith('http'): title = before
                add(url, title, url, 'itch', cats, badges)
            continue

        # Plain text (no URL)
        if re.match(r'^[-|/\\=\s]+$', s): continue
        t = re.sub(r'\s*-\s*(played|tbd)\s*$', '', s, flags=re.I)
        t = re.sub(r'\s*\([^)]*\)\s*$', '', t).replace('_', ' ').strip()
        if not t or len(t) < 2: continue
        gid = 'txt_' + re.sub(r'[^a-z0-9]', '_', t.lower())
        add(gid, t, None, 'tbd', cats, badges)

    return list(G.values())


def parse_manga_list():
    """Read manga.txt -> ordered, deduped list of (mal_id, slug, url)."""
    if not os.path.exists(MANGA_INPUT):
        return []
    entries, seen = [], set()
    with open(MANGA_INPUT, encoding='utf-8') as f:
        for raw in f:
            m = MAL_URL_RE.search(raw)
            if not m: continue
            mal_id, slug = m.group(1), m.group(2) or ''
            if mal_id in seen: continue
            seen.add(mal_id)
            entries.append((mal_id, slug, f'https://myanimelist.net/manga/{mal_id}/{slug}' if slug
                             else f'https://myanimelist.net/manga/{mal_id}'))
    return entries


def fetch_manga_info(mal_id, slug):
    """Scrape a MAL manga page for title/cover/info. Returns a dict or None on failure."""
    url = f'https://myanimelist.net/manga/{mal_id}/{slug}' if slug else f'https://myanimelist.net/manga/{mal_id}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (personal wishlist script)'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = resp.read().decode('utf-8', errors='replace')
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f'  ! failed to fetch manga {mal_id}: {e}')
        return None

    def simple(label):
        m = re.search(r'dark_text">' + label + r':</span>\s*([^<\n]+)', page)
        return html_lib.unescape(re.sub(r'\s+', ' ', m.group(1)).strip()) if m else None

    def type_field(label):
        m = re.search(r'dark_text">' + label + r':</span>\s*<a[^>]*>\s*([^<]+?)\s*</a>', page)
        return m.group(1).strip() if m else None

    def link_list(base):
        m = re.search(r'dark_text">' + base + r's?:</span>(.*?)</div>', page, re.S)
        if not m: return []
        return [html_lib.unescape(t.strip()) for t in re.findall(r'<a[^>]*title="([^"]+)"', m.group(1))]

    def authors():
        m = re.search(r'dark_text">Authors?:</span>(.*?)</div>', page, re.S)
        if not m: return []
        pairs = re.findall(r'<a href="/people/\d+/[^"]*">([^<]+)</a>\s*\(([^)]*)\)', m.group(1))
        return [[html_lib.unescape(n.strip()), html_lib.unescape(r.strip())] for n, r in pairs]

    title_m = re.search(r'og:title" content="([^"]*)"', page)
    img_m   = re.search(r'og:image" content="([^"]*)"', page)

    title_en = simple('English')

    return {
        'id': mal_id,
        'title': html_lib.unescape(title_m.group(1)) if title_m else f'Manga {mal_id}',
        'title_en': title_en,
        'url': url,
        'image': img_m.group(1) if img_m else None,
        'type': type_field('Type'),
        'volumes': simple('Volumes'),
        'chapters': simple('Chapters'),
        'status': simple('Status'),
        'published': simple('Published'),
        'genres': link_list('Genre'),
        'themes': link_list('Theme'),
        'demographics': link_list('Demographic'),
        'serializations': link_list('Serialization'),
        'authors': authors(),
    }


def load_manga_cache():
    if os.path.exists(MANGA_CACHE):
        with open(MANGA_CACHE, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_manga_cache(cache):
    with open(MANGA_CACHE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def build_manga_data(refresh=False):
    entries = parse_manga_list()
    if not entries:
        return []
    cache = {} if refresh else load_manga_cache()
    changed = False
    result = []
    for mal_id, slug, url in entries:
        if mal_id in cache and 'title_en' in cache[mal_id]:
            result.append(cache[mal_id])
            continue
        print(f'  fetching manga {mal_id} ({slug or "?"})...')
        info = fetch_manga_info(mal_id, slug)
        if info is None:
            info = {'id': mal_id, 'title': slug.replace('_', ' ') or f'Manga {mal_id}', 'title_en': None,
                     'url': url, 'image': None, 'type': None, 'volumes': None, 'chapters': None, 'status': None,
                     'published': None, 'genres': [], 'themes': [], 'demographics': [],
                     'serializations': [], 'authors': []}
        cache[mal_id] = info
        changed = True
        result.append(info)
        time.sleep(1.5)
    if changed:
        save_manga_cache(cache)
    return result


TEMPLATE = '''\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Game Wishlist</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0d0d14;color:#e0e0e0;min-height:100vh}
header{position:sticky;top:0;z-index:100;background:#11111c;border-bottom:1px solid #1c1c2c;padding:10px 18px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
#logo{font-size:.82rem;font-weight:700;color:#5050a0;white-space:nowrap;letter-spacing:.08em;text-transform:uppercase}
#search{flex:1;min-width:220px;padding:7px 13px;background:#191926;border:1px solid #2c2c48;border-radius:8px;color:#dde;font-size:.88rem;outline:none;transition:border-color .2s}
#search:focus{border-color:#5050a0}
#search::placeholder{color:#40405a}
.qw{display:flex;gap:5px;flex-wrap:wrap}
.qf{padding:4px 10px;border-radius:20px;border:1px solid #2c2c48;background:#191926;color:#505070;cursor:pointer;font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;transition:all .15s;white-space:nowrap;user-select:none}
.qf:hover{border-color:#5050a0;color:#b0b0e0}
.qf.on{background:#252558;border-color:#5050b8;color:#cccff8}
#cnt{color:#35354a;font-size:.75rem;white-space:nowrap;margin-left:auto;align-self:center}
main{padding:22px 16px;max-width:1900px;margin:0 auto}
.sec{margin-bottom:34px}
.sec-hd{display:flex;align-items:baseline;gap:8px;margin-bottom:11px;padding-bottom:6px;border-bottom:1px solid #181828}
.sec-hd h2{font-size:.75rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#4a4a78}
.sec-n{font-size:.7rem;color:#28283a}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:10px}
.card{background:#111120;border:1px solid #1c1c2c;border-radius:7px;overflow:hidden;display:flex;flex-direction:column;transition:transform .15s,border-color .15s,box-shadow .15s}
.card.has-url{cursor:pointer}
.card.has-url:hover{transform:translateY(-2px);border-color:#383860;box-shadow:0 6px 24px rgba(0,0,0,.55)}
.iw{width:100%;aspect-ratio:460/215;background:#161626;position:relative;overflow:hidden;flex-shrink:0}
.ph{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:2.8rem;font-weight:800;color:#242436;background:linear-gradient(135deg,#16162a,#0c0c18)}
.iw img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1}
.cb{padding:7px 8px;flex:1;display:flex;flex-direction:column;gap:4px}
.ct{font-size:.77rem;font-weight:600;color:#c0c0d4;line-height:1.35;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.tgs{display:flex;flex-wrap:wrap;gap:3px;margin-top:auto;padding-top:4px}
.tg{font-size:.6rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:2px 5px;border-radius:3px}
.to{background:#0b2416;color:#38925a;border:1px solid #174828}
.tp{background:#0b1a30;color:#3868a8;border:1px solid #182850}
.td{background:#2a0c0c;color:#b82a2a;border:1px solid #441414}
.tc{background:#2a1a06;color:#b07018;border:1px solid #442a0c}
.tno{background:#151520;color:#48486a;border:1px solid #22223a}
.tg2{background:#181828;color:#384060;border:1px solid #1e1e38}
.titch{background:#1e0c14;color:#a02848;border:1px solid #380e24}
.tgog{background:#1c0c28;color:#7838a8;border:1px solid #321650}
.tepic{background:#1c0e0e;color:#884848;border:1px solid #341818}
.tge{background:#0c1c2e;color:#3888c0;border:1px solid #163854}
.tth{background:#1c1030;color:#8858c8;border:1px solid #301a54}
.tdm{background:#20140a;color:#c08838;border:1px solid #402a12}
.sec.hi,.card.hi{display:none}
#nope{text-align:center;padding:80px;color:#282840;font-size:1rem;display:none}
.tabs{display:flex;gap:6px}
.tab{padding:6px 14px;border-radius:8px;border:1px solid #2c2c48;background:#191926;color:#606080;cursor:pointer;font-size:.78rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;transition:all .15s;user-select:none}
.tab:hover{border-color:#5050a0;color:#b0b0e0}
.tab.on{background:#252558;border-color:#5050b8;color:#cccff8}
.manga-iw{aspect-ratio:225/319}
.ct-sub{font-size:.68rem;font-weight:500;color:#68688e;line-height:1.3;margin-top:-2px}
.minfo{font-size:.68rem;color:#7878a0;line-height:1.5}
.minfo b{color:#9a9ac8;font-weight:700}
.mauth{font-size:.65rem;color:#585884;line-height:1.4}
</style>
</head>
<body>
<header>
  <span id="logo">Wishlist</span>
  <div class="tabs">
    <button class="tab on" data-tab="games">Games</button>
    <button class="tab" data-tab="manga">Manga</button>
  </div>
  <input id="search" type="text" placeholder="search title, category, badge… (owned · denuvo · played · ps1)" autocomplete="off" spellcheck="false">
  <div class="qw" id="qw-games">
    <button class="qf on" data-f="">All</button>
    <button class="qf" data-f="owned">Owned</button>
    <button class="qf" data-f="played">Played</button>
    <button class="qf" data-f="denuvo">Denuvo</button>
    <button class="qf" data-f="cracked">Cracked</button>
    <button class="qf" data-f="tbd">No Link</button>
    <button class="qf" data-f="ps1">PS1</button>
    <button class="qf" data-f="itch">Itch.io</button>
  </div>
  <div class="qw" id="qw-manga" style="display:none">
    <button class="qf on" data-f="">All</button>
    <button class="qf" data-f="publishing">Publishing</button>
    <button class="qf" data-f="finished">Finished</button>
  </div>
  <span id="cnt"></span>
</header>
<main id="main-games"></main>
<main id="main-manga" style="display:none"></main>
<div id="nope">No games found.</div>

<script>
const G = __GAMES_DATA__;
const M = __MANGA_DATA__;

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}

const catMap = new Map();
for(const g of G){
  const c = (g.categories && g.categories[0]) || 'Other';
  if(!catMap.has(c)) catMap.set(c,[]);
  catMap.get(c).push(g);
}

function tagHtml(g){
  const parts = [];
  for(const b of g.badges){
    const cls = b==='owned'?'to':b==='played'?'tp':b==='denuvo'?'td':b==='cracked'?'tc':'tno';
    parts.push(`<span class="tg ${cls}">${b}</span>`);
  }
  if(g.type==='itch') parts.push('<span class="tg titch">itch</span>');
  if(g.type==='gog')  parts.push('<span class="tg tgog">gog</span>');
  if(g.type==='epic') parts.push('<span class="tg tepic">epic</span>');
  if(g.type==='tbd')  parts.push('<span class="tg tno">no link</span>');
  for(const c of g.categories.slice(1))
    parts.push(`<span class="tg tg2">${esc(c)}</span>`);
  return parts.join('');
}

function buildGamesDOM(){
  let html='';
  for(const [cat,games] of catMap){
    const cards = games.map((g,li)=>{
      const urlCls = g.url ? ' has-url' : '';
      const imgHtml = g.image
        ? `<img src="${esc(g.image)}" alt="" loading="lazy">`
        : '';
      return `<div class="card${urlCls}" data-i="${li}" data-cat="${esc(cat)}">
<div class="iw"><div class="ph">${esc(g.title.charAt(0).toUpperCase())}</div>${imgHtml}</div>
<div class="cb"><div class="ct">${esc(g.title)}</div><div class="tgs">${tagHtml(g)}</div></div>
</div>`;
    }).join('');
    html += `<section class="sec" data-cat="${esc(cat)}">
<div class="sec-hd"><h2>${esc(cat)}</h2><span class="sec-n">${games.length}</span></div>
<div class="grid">${cards}</div>
</section>`;
  }
  document.getElementById('main-games').innerHTML = html;

  // Build per-card search strings and attach click
  let secIdx=0;
  for(const sec of document.querySelectorAll('#main-games .sec')){
    const cat = [...catMap.keys()][secIdx++];
    const games = catMap.get(cat);
    sec.querySelectorAll('.card').forEach((el,i)=>{
      const g = games[i];
      el._s = [g.title,...g.categories,...g.badges,g.type].join(' ').toLowerCase();
      if(g.url) el.addEventListener('click',()=>window.open(g.url,'_blank'));
    });
  }
}

function mangaSortKey(m){
  return (m.title_en || m.title || '').toLowerCase();
}

const mangaStatusMap = new Map();
for(const m of M){
  const s = m.status || 'Unknown';
  if(!mangaStatusMap.has(s)) mangaStatusMap.set(s,[]);
  mangaStatusMap.get(s).push(m);
}
for(const arr of mangaStatusMap.values())
  arr.sort((a,b)=>mangaSortKey(a).localeCompare(mangaSortKey(b)));

function mangaOrder(a,b){
  const order=['Publishing','Finished'];
  const ia=order.indexOf(a), ib=order.indexOf(b);
  if(ia===-1 && ib===-1) return a.localeCompare(b);
  if(ia===-1) return 1;
  if(ib===-1) return -1;
  return ia-ib;
}

function mangaMetaLine(m){
  const bits=[];
  if(m.type) bits.push(`<b>${esc(m.type)}</b>`);
  if(m.volumes) bits.push(`${esc(m.volumes)} vol`);
  if(m.chapters) bits.push(`${esc(m.chapters)} ch`);
  return bits.join(' · ');
}

function buildMangaDOM(){
  let html='';
  const keys=[...mangaStatusMap.keys()].sort(mangaOrder);
  for(const st of keys){
    const items = mangaStatusMap.get(st);
    const cards = items.map((m,li)=>{
      const urlCls = m.url ? ' has-url' : '';
      const imgHtml = m.image ? `<img src="${esc(m.image)}" alt="" loading="lazy">` : '';
      const chips = [
        ...(m.demographics||[]).map(d=>`<span class="tg tdm">${esc(d)}</span>`),
        ...(m.genres||[]).map(g=>`<span class="tg tge">${esc(g)}</span>`),
        ...(m.themes||[]).map(t=>`<span class="tg tth">${esc(t)}</span>`),
      ].join('');
      const authors = (m.authors||[]).map(a=>a[1]?`${a[0]} (${a[1]})`:a[0]).join(', ');
      const meta = mangaMetaLine(m);
      const titleEn = m.title_en && m.title_en.toLowerCase()!==(m.title||'').toLowerCase() ? m.title_en : null;
      return `<div class="card${urlCls}" data-i="${li}">
<div class="iw manga-iw"><div class="ph">${esc((m.title||'?').charAt(0).toUpperCase())}</div>${imgHtml}</div>
<div class="cb">
<div class="ct">${esc(m.title||'Unknown')}</div>
${titleEn?`<div class="ct-sub">${esc(titleEn)}</div>`:''}
<div class="minfo">${meta}${m.published?`<br>${esc(m.published)}`:''}${(m.serializations&&m.serializations.length)?`<br>${esc(m.serializations.join(', '))}`:''}</div>
${authors?`<div class="mauth">${esc(authors)}</div>`:''}
<div class="tgs">${chips}</div>
</div>
</div>`;
    }).join('');
    html += `<section class="sec" data-cat="${esc(st)}">
<div class="sec-hd"><h2>${esc(st)}</h2><span class="sec-n">${items.length}</span></div>
<div class="grid">${cards}</div>
</section>`;
  }
  document.getElementById('main-manga').innerHTML = html;

  let secIdx=0;
  for(const sec of document.querySelectorAll('#main-manga .sec')){
    const st = keys[secIdx++];
    const items = mangaStatusMap.get(st);
    sec.querySelectorAll('.card').forEach((el,i)=>{
      const m = items[i];
      el._s = [m.title,m.title_en,m.type,m.status,m.published,...(m.genres||[]),...(m.themes||[]),
               ...(m.demographics||[]),...(m.serializations||[]),...(m.authors||[]).map(a=>a[0])]
              .filter(Boolean).join(' ').toLowerCase();
      if(m.url) el.addEventListener('click',()=>window.open(m.url,'_blank'));
    });
  }
}

buildGamesDOM();
buildMangaDOM();

let activeTab='games', qfGames='', qfManga='';

function doFilter(containerSel,text,quick,label){
  const terms=(text+' '+quick).trim().toLowerCase().split(/\\s+/).filter(Boolean);
  let total=0;
  for(const sec of document.querySelectorAll(containerSel+' .sec')){
    let n=0;
    for(const card of sec.querySelectorAll('.card')){
      const match=!terms.length||terms.every(t=>card._s.includes(t));
      card.classList.toggle('hi',!match);
      if(match) n++;
    }
    sec.classList.toggle('hi',n===0);
    const el=sec.querySelector('.sec-n');
    if(el) el.textContent=n;
    total+=n;
  }
  document.getElementById('cnt').textContent=total+' '+label;
  document.getElementById('nope').style.display=total?'none':'block';
}

function refresh(){
  if(activeTab==='games') doFilter('#main-games',inp.value,qfGames,'games');
  else doFilter('#main-manga',inp.value,qfManga,'manga');
}

const inp=document.getElementById('search');
inp.addEventListener('input',refresh);

document.querySelectorAll('#qw-games .qf').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('#qw-games .qf').forEach(b=>b.classList.remove('on'));
    btn.classList.add('on');
    qfGames=btn.dataset.f;
    refresh();
  });
});
document.querySelectorAll('#qw-manga .qf').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('#qw-manga .qf').forEach(b=>b.classList.remove('on'));
    btn.classList.add('on');
    qfManga=btn.dataset.f;
    refresh();
  });
});

document.querySelectorAll('.tab').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.tab').forEach(b=>b.classList.remove('on'));
    btn.classList.add('on');
    activeTab=btn.dataset.tab;
    document.getElementById('main-games').style.display=activeTab==='games'?'':'none';
    document.getElementById('main-manga').style.display=activeTab==='manga'?'':'none';
    document.getElementById('qw-games').style.display=activeTab==='games'?'':'none';
    document.getElementById('qw-manga').style.display=activeTab==='manga'?'':'none';
    inp.placeholder=activeTab==='games'
      ? 'search title, category, badge… (owned · denuvo · played · ps1)'
      : 'search title, genre, theme, author, status…';
    refresh();
  });
});

refresh();
</script>
</body>
</html>
'''

def main():
    refresh_manga = '--refresh-manga' in sys.argv
    games = parse()
    print(f'Parsed {len(games)} games')
    cats = {}
    for g in games:
        c = g['categories'][0] if g['categories'] else 'Other'
        cats[c] = cats.get(c,0)+1
    for c,n in cats.items():
        print(f'  {c}: {n}')

    manga = build_manga_data(refresh=refresh_manga)
    print(f'Parsed {len(manga)} manga')

    html = TEMPLATE.replace('__GAMES_DATA__', json.dumps(games, ensure_ascii=False))
    html = html.replace('__MANGA_DATA__', json.dumps(manga, ensure_ascii=False))
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\nWrote: {OUTPUT}')

main()
