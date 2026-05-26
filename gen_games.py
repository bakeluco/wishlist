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
"""

import re, json, os

INPUT  = os.path.join(os.path.dirname(__file__), 'list_of_games.txt')
OUTPUT = os.path.join(os.path.dirname(__file__), 'index.html')

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
.sec.hi,.card.hi{display:none}
#nope{text-align:center;padding:80px;color:#282840;font-size:1rem;display:none}
</style>
</head>
<body>
<header>
  <span id="logo">Wishlist</span>
  <input id="search" type="text" placeholder="search title, category, badge… (owned · denuvo · played · ps1)" autocomplete="off" spellcheck="false">
  <div class="qw">
    <button class="qf on" data-f="">All</button>
    <button class="qf" data-f="owned">Owned</button>
    <button class="qf" data-f="played">Played</button>
    <button class="qf" data-f="denuvo">Denuvo</button>
    <button class="qf" data-f="cracked">Cracked</button>
    <button class="qf" data-f="tbd">No Link</button>
    <button class="qf" data-f="ps1">PS1</button>
    <button class="qf" data-f="itch">Itch.io</button>
  </div>
  <span id="cnt"></span>
</header>
<main id="main"></main>
<div id="nope">No games found.</div>

<script>
const G = __DATA__;

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

function buildDOM(){
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
  document.getElementById('main').innerHTML = html;

  // Build per-card search strings and attach click
  let secIdx=0;
  for(const sec of document.querySelectorAll('.sec')){
    const cat = [...catMap.keys()][secIdx++];
    const games = catMap.get(cat);
    sec.querySelectorAll('.card').forEach((el,i)=>{
      const g = games[i];
      el._s = [g.title,...g.categories,...g.badges,g.type].join(' ').toLowerCase();
      if(g.url) el.addEventListener('click',()=>window.open(g.url,'_blank'));
    });
  }
}

buildDOM();

let qf='';
function doFilter(text,quick){
  const terms=(text+' '+quick).trim().toLowerCase().split(/\\s+/).filter(Boolean);
  let total=0;
  for(const sec of document.querySelectorAll('.sec')){
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
  document.getElementById('cnt').textContent=total+' games';
  document.getElementById('nope').style.display=total?'none':'block';
}

doFilter('','');

const inp=document.getElementById('search');
inp.addEventListener('input',()=>doFilter(inp.value,qf));
for(const btn of document.querySelectorAll('.qf')){
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.qf').forEach(b=>b.classList.remove('on'));
    btn.classList.add('on');
    qf=btn.dataset.f;
    doFilter(inp.value,qf);
  });
}
</script>
</body>
</html>
'''

def main():
    games = parse()
    print(f'Parsed {len(games)} games')
    cats = {}
    for g in games:
        c = g['categories'][0] if g['categories'] else 'Other'
        cats[c] = cats.get(c,0)+1
    for c,n in cats.items():
        print(f'  {c}: {n}')
    data_json = json.dumps(games, ensure_ascii=False)
    html = TEMPLATE.replace('__DATA__', data_json)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\nWrote: {OUTPUT}')

main()
