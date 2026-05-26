Reads list_of_games.txt and writes index.html — a visual gallery with Steam cover art.
--------------------------

[Open wishlist...](https://bakeluco.github.io/wishlist/)

HOW TO RUN:
--------------------------
1) Create a virtual environment:

        python3 -m venv venv

2) Activate the virtual environment:

        source venv/bin/activate

3) Install your packages inside the virtual environment:

        pip install ....

REGENERATE AFTER ANY EDIT
--------------------------
    python3 gen_games.py

- Commit both list_of_games.txt and index.html to GitHub.
- GitHub Pages will serve index.html automatically.
- Tip: rename index.html → index.html in your repo so the root URL opens it directly.

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
    https://store.steampowered.com/app/2358720/Black_Myth_Wukong/ (denuvo)

Recognised badge words:
- owned   → green  — you own it
- played  → blue   — you've finished / played it
- denuvo  → red    — has Denuvo DRM
- cracked → orange — Denuvo gone / cracked

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

- Edit list_of_games.txt — add/remove/badge games
- Run python3 gen_games.py — regenerates index.html
-       git add list_of_games.txt index.html && git commit && git push
- For GitHub Pages: go to your repo's Settings → Pages → set source to the main branch root. 
- Rename index.html to index.html in the repo if you want username.github.io/reponame to open it directly without a /index.html suffix.

Common edits in list_of_games.txt:
- Beat a game → append (played) to its line
- Bought a game → append (owned) to its line
- Add a new game → paste the Steam URL under the right -CATEGORY- header
- Remove a game → delete the line
- Add a game you can't find yet → just write its name as plain text