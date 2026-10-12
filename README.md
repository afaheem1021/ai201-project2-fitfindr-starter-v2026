# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools and the loop are built now, so that last command finds a
> listing, suggests outfits and writes a fit card.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

You tell FitFindr what you're hunting for in normal words, like `'vintage graphic tee under $30, size L'`, and it pulls the price and size out of that and searches 40 thrift listings from depop, thredUp and poshmark. It takes the best match and comes up with two outfits for it using stuff already in your closet (or general ideas if your closet is empty). Then it writes a short caption you could actually post with the fit, with the price and where you got it. If nothing matches, it stops there and tells you what to change, like raising your budget to a specific number or dropping the size.


---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Looks through `data/listings.json` and returns the listings that match the user's keywords, filtered by size and price if they gave one, best match first.
- **Inputs:** `description` (str) - the keywords, like "vintage graphic tee". `size` (str or None) - a size like "M", "8" or "W30", None means don't filter on size. `max_price` (float or None) - the price ceiling, inclusive, None means no ceiling.
- **Returns:** A `list[dict]` of listing dicts, sorted by keyword score highest first, at most `config.SEARCH_RESULT_LIMIT` (10). Each dict is the full listing straight from the data: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price` (float), `colors`, `brand` (can be None), `platform`.
  - Size match rule: I split the listing's size into tokens on `/`, spaces and parentheses, and the size has to equal one of those tokens. So "M" matches `M`, `S/M` and `M/L` but not `XL`. A number like "8" matches `US 8` but not `US 8.5`, and "30" or "W30" both match `W30 L30`. Listings that say "One Size" count as a match for any letter size (S, M, L...) but not for a shoe or waist size.
  - Score: a keyword hit in the title or style tags is worth 2, a hit in the description, colors or category is worth 1, and +3 if the whole phrase shows up in the title in order. Filler words ("looking", "for", "a", "the"...) are dropped before scoring, and anything that scores 0 is dropped.
- **When it has nothing:** An empty list `[]`. Never None and never an exception.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new item, using pieces the user already owns.
- **Inputs:** `new_item` (dict) - one listing dict, the same shape search returns. `wardrobe` (dict) - `{"items": [...]}` where each item has `name`, `category`, `colors`, `style_tags`, `notes`.
- **Returns:** A non-empty `str` of outfit ideas (plain text, a few short lines). With a real wardrobe it names actual pieces from the wardrobe by name.
- **When it has nothing:** If `wardrobe["items"]` is empty it does NOT fail, it asks the model for general styling advice for the item instead (what kinds of pieces go with it) and returns that string. If `new_item` is empty or None it returns an empty string `""` so the caller can tell nothing happened.

### `create_fit_card`

- **What it does:** Writes a short, casual caption about the find, the kind of thing someone would actually post on Instagram or TikTok.
- **Inputs:** `outfit` (str) - what suggest_outfit returned. `new_item` (dict) - the listing dict for the item.
- **Returns:** A `str` caption, 2 to 4 sentences, that mentions the item, its price (like "$24") and the platform (like "depop") once each.
- **When it has nothing:** If `outfit` is empty or only whitespace it doesn't call the model, it returns the string `"Can't make a fit card yet - there's no outfit to build it from."`

---

## Planning Loop

**Branch rule:** If `search_listings` returns an empty list, I put a message in `session["error"]` that says what to change and stop, `suggest_outfit` never gets called. To make the message useful, before stopping the loop re-runs the search with the size dropped and then with the price dropped, so it can tell the user which filter killed it ("there's 3 matches if you go up to $45" vs "nothing matches those words at all, try different ones"). Otherwise (the list is not empty), take the first result as `session["selected_item"]` and go on to `suggest_outfit`, then `create_fit_card`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex, in `agent.py::parse_query`. It pulls out a price ("under $30", "below 30", "max $25", "less than $40", "$20 or less") and a size ("size M", "in size 8", "size W30"), then whatever's left over is the description.

**Things I already know are shaky (for next unit):** the search counts any one keyword hit, so `'leather bomber size M under $50'` comes back with a braided leather belt, because the only leather bomber is $75 and the belt matches on "leather" alone (and "One Size" counts as M). And "t-shirt" doesn't find tees because there's no synonym handling.

**What moves through the session:** `query` -> `parsed` (description, size, max_price) -> `search_results` -> `selected_item` -> `outfit_suggestion` -> `fit_card`. On the empty path it's `query` -> `parsed` -> `search_results` (empty) -> `error`, and `selected_item`, `outfit_suggestion` and `fit_card` stay None. I also added `tool_calls`, a list where every tool call logs its name and the id of the item it was given, so I can check later that the item search found is the one the other two tools actually got.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30, size L'

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   Outfit 1: Graphic Tee paired with baggy straight-leg jeans, black combat boots, and black crossbody bag.
Outfit 2: Graphic Tee paired with wide-leg khaki trousers, vintage black denim jacket, and chunky white sneakers.

  Fit card: Paired this 2003 tour tee with baggy jeans and combat boots. Total steal on depop for just $24. 🎸

#thriftfind #ootd #streetwear

2 model calls this session, 608 prompt + 88 output tokens
```

And the same thing with a query that can't match, which stops before the model ever gets called:

```
$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing in the listings matches 'designer ballgown' in size XXS under $5, and nothing matches 'designer ballgown' even with no size or price limit, so it's the words. Try naming the type of piece (tee, jacket, jeans, boots, cardigan) or a style (vintage, y2k, grunge, 90s).

0 model calls this session

$ python app.py ask 'denim jacket size XL'

  I couldn't find 'denim jacket' in size XL. You could drop the size: there's 8 match(es) in other sizes (M, M/L, S, W27).

0 model calls this session
```

Checking the state (that the item search found is the one the other tools got), from `session["tool_calls"]`:

```
$ python -c "from agent import run_agent; from utils.data_loader import get_example_wardrobe as w; s=run_agent('vintage graphic tee under \$30, size L', w()); print(s['search_results'][0]['id'], s['selected_item']['id']); [print(c) for c in s['tool_calls']]"
lst_006 lst_006
{'tool': 'search_listings', 'inputs': {'description': 'vintage graphic tee', 'size': 'L', 'max_price': 30.0}, 'result_count': 5}
{'tool': 'suggest_outfit', 'item_id': 'lst_006', 'wardrobe_size': 10}
{'tool': 'create_fit_card', 'item_id': 'lst_006'}
```

**The three tools, tested one at a time**

search_listings, a normal search and then the empty case:

```
$ python -c "from tools import search_listings; print([(r['id'], r['title'], r['price'], r['size'], r['platform']) for r in search_listings('graphic tee', max_price=30)])"
[('lst_006', 'Graphic Tee — 2003 Tour Bootleg Style', 24.0, 'L', 'depop'), ('lst_002', 'Y2K Baby Tee — Butterfly Print', 18.0, 'S/M', 'depop'), ('lst_033', 'Vintage Band Tee — Faded Grey', 19.0, 'L', 'depop'), ('lst_015', 'Vintage Graphic Hoodie — Faded Black', 26.0, 'L', 'depop'), ('lst_017', 'Mesh Long-Sleeve Top — Black', 15.0, 'S/M', 'depop'), ('lst_011', 'Low-Rise Cargo Pants — Khaki', 27.0, 'W29', 'poshmark'), ('lst_012', 'Oversized Crewneck Sweatshirt — Vintage Navy', 20.0, 'XL (fits oversized)', 'thredUp')]

$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

(I printed a few fields instead of the whole dicts because the full thing is a wall of text. The cargo pants and the sweatshirt are in there because "graphic" or "tee" shows up somewhere in their descriptions, they're low scores so they end up at the bottom.)

suggest_outfit, with the example wardrobe and then the empty one:

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_example_wardrobe()))"
Outfit 1: Graphic Tee paired with baggy straight-leg jeans, brown leather belt, and black combat boots.
Outfit 2: Graphic Tee layered under vintage black denim jacket with wide-leg khaki trousers and chunky white sneakers.

$ python -c "from tools import suggest_outfit; from utils.data_loader import get_empty_wardrobe, load_listings; print(suggest_outfit(load_listings()[5], get_empty_wardrobe()))"
Outfit 1: Pair it with high-waisted light wash mom jeans, chunky black platform boots, and a silver chain necklace.
Outfit 2: Layer it over a long-sleeve black mesh top with a plaid midi skirt, worn Converse sneakers, and a beanie.
```

create_fit_card, run three times with the cache off (`AI201_CACHE=0`) so I'd see if it was actually varying, then the empty outfit case:

```
$ AI201_CACHE=0 python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('baggy dark wash jeans, black combat boots and the black denim jacket', load_listings()[5]))"
That 2003 tour bootleg graphic tee looks so good with baggy dark wash jeans. Snagged this gem on depop for just $24. Total win for today's fit. 🖤🎸 #thriftfinds #streetwear #depopstyle

(2nd run)
That 2003 tour bootleg graphic tee looks so good with baggy dark wash jeans. Got it on depop for just $24. Total win for today's fit. 🖤

#vintage #streetwear #depopfinds

(3rd run)
This 2003 tour bootleg tee is way too good. Snagged it on depop for just $24. Paired it with baggy dark wash jeans for today's fit. 🖤

#depopfinds #streetwear #thrifted

$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('   ', load_listings()[5]))"
Can't make a fit card yet - there's no outfit to build it from.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

I used Claude for this project, mostly to write the first drafts of the tools and the loop from my spec, and then I ran everything myself and fixed what didn't look right.

**Moment 1**

- *What I asked for:* I gave Claude my `create_fit_card` spec (2-4 sentences, mention the price and platform once each, sound like a real post) and had it write the prompt. Then I ran it three times on the same graphic tee with `AI201_CACHE=0` so the cache couldn't fake the variety.
- *What came back:* Three different captions, but all three opened with "Scored this 2003 tour bootleg tee on depop for just $24" and the second half was basically the same too. They also all had `#depop` as a hashtag, so the platform showed up twice even though the spec says once.
- *What I changed:* I added two rules to the prompt: don't hashtag the platform, and don't open with "Scored", "Just thrifted" or "Obsessed", start with something about the piece instead. After that the openings changed ("That 2003 tour bootleg graphic tee looks so good...", "This 2003 tour bootleg tee is way too good...") and depop only showed up once in the sentence. They're still kind of similar to each other honestly, which is exactly what criterion 4 is going to test next unit.

**Moment 2**

- *What I asked for:* For the empty-search message I didn't want to just trust that it was good, so I did what Milestone 5 says and pasted my ballgown message into the model with the "I know nothing about how the app works, tell me what I would try next" prompt.
- *What came back:* It said it would try a broader item type from the examples in the message (tee, jacket, jeans) or a style word (vintage, y2k, 90s). So the message was doing its job for that case. But when I tried `'graphic tee size XS under $10'` myself, the message just said "loosen both the size and the price" which doesn't really tell you how much.
- *What I changed:* For that case (where dropping either filter alone still finds nothing) I made the message name the closest real listing, so now it says "the closest thing is the Graphic Tee — 2003 Tour Bootleg Style in size L for $24." I also had the loop re-run the search with each filter dropped so it can say which one killed it, instead of a generic "no results".

One smaller thing: the first version of `suggest_outfit` came back with "Hey babe! That butterfly baby tee is a total thrift score..." before the actual outfits. Fun but not what I asked for, so I added "Reply with only those two lines, no intro" to both versions of the prompt.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

Ran with `python run_eval.py --label before`: every scenario in `scenarios.py` 5 times, cache off, temperature 0.9. 91 real model calls, nothing served from cache, no crashes. The full log is [results/run_2026-10-11_2209_before.md](results/run_2026-10-11_2209_before.md).

`run_eval.py` leaves PASS/FAIL blank, so I wrote [check_run.py](check_run.py) to apply each criterion the way it's worded in `criteria.md` and print the reason for every try (`python check_run.py results/run_2026-10-11_2209_before.md`). I didn't want to eyeball 50 tries and miss something, but I also read every fit card and outfit myself, which is how I found the stuff in the diagnoses section.

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools and returns a fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before suggest_outfit, message names what to change | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item id in search_results[0], selected_item, suggest_outfit and create_fit_card | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card has exact price + platform and is 280 chars or less (and the 5 don't all open the same) | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 5. Price ceiling parsed right and respected, 5 phrasings | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Notes on how I read the table:
- **Criterion 5** is written as one try per phrasing, so Try 1-5 are `'graphic tee under $30'`, `'denim jacket below 50'`, `'cardigan max $40'`, `'platform sneakers less than $60'`, `'band tee $20 or less'`. `run_eval` actually ran each phrasing 5 times (25 runs) and all 25 passed, the parsed max_price and the price range were identical every time, which makes sense since no model is involved in that part.
- **Criterion 4**: all 5 cards had `$42` and `poshmark`, lengths were 222, 188, 201, 178, 171. The first 5 words were different on all 5 (`this cropped light wash denim`, `cropped light wash denim is`, `that light wash cropped denim`, `the wash on this cropped`, `double denim is back with`).
- The empty wardrobe scenario isn't one of my five, but it completed 5/5 with general advice and the "you don't have any wardrobe items saved" line every time.

**Real output from one try of each**, all produced by `agent.py::run_agent` (through `run_eval.py::run_once`), copied out of the run log:

Criterion 1, try 1 (`'vintage graphic tee under $30'`):
```
[1] parse_query
      in:  vintage graphic tee under $30
      out: {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': None, 'max_price': 30.0}
      out: 10 items: Y2K Baby Tee — Butterfly Print, Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey … +7 more
      →    branch: 10 results (prices $12-$30), selected_item = lst_002, going to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_002 (Y2K Baby Tee — Butterfly Print), wardrobe=10 items
      out: Outfit 1: Y2K Baby Tee — Butterfly Print paired with Baggy straight-leg jeans, dark wash, Vintage black denim …
[4] create_fit_card
      in:  new_item=lst_002, outfit=<from suggest_outfit>
      out: Threw on this butterfly tee with baggy dark denim and chunky white sneakers for the ultimate Y2K fit. Snagged …
      →    done

Fit card: Threw on this butterfly tee with baggy dark denim and chunky white sneakers for the ultimate Y2K fit. Snagged it on depop for just $18! 🦋✨ #y2kstyle #depopfinds #streetwear
```

Criterion 2, try 1 (`'designer ballgown size XXS under $5'`):
```
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
[2] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': 'XXS', 'max_price': 5.0}
      out: [] (empty)
      →    branch: empty, working out what to tell the user, then stopping
[3] search_listings (via MCP)
      in:  {'description': 'designer ballgown', 'size': None, 'max_price': None}
      out: [] (empty)
      →    re-search with a filter dropped, to see which one emptied it
[4] stop
      out: Nothing in the listings matches 'designer ballgown' in size XXS under $5, and nothing matches 'designer ballgo…
      →    suggest_outfit never called

session["error"]: Nothing in the listings matches 'designer ballgown' in size XXS under $5, and nothing matches 'designer ballgown' even with no size or price limit, so it's the words. Try naming the type of piece (tee, jacket, jeans, boots, cardigan) or a style (vintage, y2k, grunge, 90s).
session["fit_card"]: None
```

Criterion 3, try 1 (`'90s track jacket in size M'`), lst_004 is search_results[0], selected_item, and what both later tools got:
```
[1] parse_query
      in:  90s track jacket in size M
      out: {'description': '90s track jacket', 'size': 'M', 'max_price': None}
[2] search_listings (via MCP)
      in:  {'description': '90s track jacket', 'size': 'M', 'max_price': None}
      out: 5 items: 90s Track Jacket — Navy/White Stripe, 90s Leather Bomber — Black, 90s Silk Slip Dress — Floral, Midi Length … +2 more
      →    branch: 5 results (prices $14-$75), selected_item = lst_004, going to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_004 (90s Track Jacket — Navy/White Stripe), wardrobe=10 items
      out: Outfit 1: Pair the 90s Track Jacket with the white ribbed tank top, baggy straight-leg jeans, and chunky white…
[4] create_fit_card
      in:  new_item=lst_004, outfit=<from suggest_outfit>
      out: That navy and white 90s track jacket was such a steal on poshmark for only $45. Throwing it on with a white ri…
      →    done
```

Criterion 4, try 1 (`'denim jacket under $50'`), the card from `tools.py::create_fit_card`:
```
This cropped light wash denim jacket was only $42 on poshmark and fits like a dream. Paired it with wide-leg khaki trousers, a white ribbed tank, and combat boots for an easy everyday fit. 🧥✨ #denimstyle #thriftfinds #ootd
```
(`check_run.py` said: has $42 + poshmark, 222 chars)

Criterion 5, phrasing 2 (`'denim jacket below 50'`), parse and search steps:
```
[1] parse_query
      in:  denim jacket below 50
      out: {'description': 'denim jacket', 'size': None, 'max_price': 50.0}
[2] search_listings (via MCP)
      in:  {'description': 'denim jacket', 'size': None, 'max_price': 50.0}
      out: 7 items: Denim Jacket — Light Wash, Cropped, Vintage Levi's 501 Jeans — Medium Wash, 90s Track Jacket — Navy/White Stripe … +4 more
      →    branch: 7 results (prices $24-$45), selected_item = lst_007, going to suggest_outfit
```

---

## Verdicts and Diagnoses

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Matching query completes all 3 tools + fit card | 4 of 5 | MET (5/5) | All 5 traces have search, suggest_outfit and create_fit_card steps and a non-empty fit card. No early stops, no crashes. |
| 2 | Impossible query stops before suggest_outfit, names what to change | 5 of 5 | MET (5/5) | All 5 stopped after the search, no suggest_outfit step in any trace, fit_card stayed None, and the message says "it's the words" and gives words to try. |
| 3 | Same item id all the way through | 5 of 5 | MET (5/5) | lst_004 was the first search result, selected_item, and the `new_item` id in both the suggest_outfit and create_fit_card steps on all 5 tries. |
| 4 | Fit card has $price + platform, 280 chars or less | 4 of 5 | MET (5/5) | All 5 had `$42` and `poshmark`, longest was 222 chars, and the 5 openings were all different. |
| 4 (revised) | Same, plus no stock "snagged it on poshmark for $42" sentence | 4 of 5 | **MISSED (1/5)** | Only try 1 passed. Tries 2-5 had "Found this gem on poshmark for only $42", "Snagged this gem on poshmark for just $42", "Snagged it on poshmark for $42", "found on poshmark for only $42". |
| 5 | Price ceiling parsed and respected, 5 phrasings | 5 of 5 | MET (5/5) | Every phrasing parsed to the number I typed, and the most expensive result was under it every time (e.g. below 50 -> $24-$45). Same on all 25 runs. |

**Diagnoses**

*Criterion 4 (revised), missed 1/5.* Where: the model's output, in `tools.py::create_fit_card`. The tool itself works and the loop passes it the right item every time (criterion 3 shows that). The mechanism is the prompt. One of my rules is "say the price exactly as $42 and the platform name 'poshmark', once each", so the model treats price and platform as two facts it has to slot in. The easiest way to do both in a caption is the sentence every thrift post already uses, "snagged it on poshmark for just $42". It's not about this one jacket either: across the whole before run 28 of 45 cards had that sentence, on every item (baby tee, track jacket, cardigan, sneakers, band tee...). So it's one problem in one prompt, not nine.

The funny part is I sort of caused this in unit 3. Back then the cards opened with "Scored this 2003 tour bootleg tee on depop for just $24", so I banned "Scored" / "Just thrifted" as openers. That fixed the opening and my first-5-words check, but the same phrase just moved to the second sentence where my criterion wasn't looking. That's also why the original criterion 4 passed so easily.

**I didn't miss any of the original five, so being honest about my targets:**
- Criteria 2, 3 and 5 test code that doesn't touch the model (an `if not results`, reading a dict out of the session, a regex and a `<=`). Once the code is right they pass every single time, which is what happened, 5/5 and 25/25. They're good at catching a bug if I break something later, but they couldn't really tell me anything new this time.
- Criterion 1 was low. 4 of 5 on a query I'd already checked against the data is pretty safe. The miss I was expecting was from my keyword search on a weird phrasing, and my test only used the one phrasing I knew worked. If I tightened it I'd make it 5 different matching queries I haven't tried before.
- Criterion 4 was the loosest. The cards were 154-232 characters against a 280 limit, and all 45 cards in the run had the price and the platform. That's why it's the one I revised.

**Things I saw that none of my criteria cover** (not misses, but they're real):
- `suggest_outfit` ignored "no intro" 2 times out of 45 and started with "Hey babe, grab that tee! It's such a fun find..." and "Hey friend! Those chunky platform sneakers...". I think the system prompt calling it a "friendly stylist who's really into thrifting" pulls it toward that.
- One wardrobe item is named "Baggy straight-leg jeans, dark wash", with a comma in the name. The outfit lists it as "...Baggy straight-leg jeans, dark wash, Vintage black denim jacket...", and in one card that turned into "my baggy jeans, dark wash jacket, and chunky sneakers", which is a jacket the user doesn't own.
- For `'vintage graphic tee under $30'` the agent picks the Y2K butterfly baby tee over the actual "Graphic Tee — 2003 Tour Bootleg Style", because the baby tee has both "vintage" and "graphic tee" in its tags. It's not wrong exactly, but it's probably not what I'd want.

---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

Every step calls `trace.step()` inside `agent.py::run_agent` (and inside `_no_results_message` for the extra searches). The search steps say "(via MCP)" because that's the tool that goes through `mcp_server.py` now.

**Happy path**

```
$ python app.py ask 'vintage graphic tee under $30, size L' --trace
[1] parse_query
      in:  vintage graphic tee under $30, size L
      out: {'description': 'vintage graphic tee', 'size': 'L', 'max_price': 30.0}
[2] search_listings (via MCP)
      in:  {'description': 'vintage graphic tee', 'size': 'L', 'max_price': 30.0}
      out: 5 items: Graphic Tee — 2003 Tour Bootleg Style, Vintage Band Tee — Faded Grey, Vintage Graphic Hoodie — Faded Black … +2 more
      →    branch: 5 results, selected_item = lst_006, going to suggest_outfit
[3] suggest_outfit
      in:  new_item=lst_006 (Graphic Tee — 2003 Tour Bootleg Style), wardrobe=10 items
      out: Outfit 1: Graphic Tee paired with baggy straight-leg jeans, black combat boots, and black crossbody bag. Outfi…
[4] create_fit_card
      in:  new_item=lst_006, outfit=<from suggest_outfit>
      out: Paired this 2003 tour tee with baggy jeans and combat boots. Total steal on depop for just $24. 🎸  #thriftfind…
      →    done

  Found:    Graphic Tee — 2003 Tour Bootleg Style — $24.0 on depop

  Outfit:   Outfit 1: Graphic Tee paired with baggy straight-leg jeans, black combat boots, and black crossbody bag.
Outfit 2: Graphic Tee paired with wide-leg khaki trousers, vintage black denim jacket, and chunky white sneakers.

  Fit card: Paired this 2003 tour tee with baggy jeans and combat boots. Total steal on depop for just $24. 🎸

#thriftfind #ootd #streetwear

0 model calls this session, 2 served from cache
```

(This one says "served from cache" because I'd already run the same query while building. The eval runs below have the cache off.)

**Empty search**

```
$ python app.py ask 'graphic tee size XS under $10' --trace
[1] parse_query
      in:  graphic tee size XS under $10
      out: {'description': 'graphic tee', 'size': 'XS', 'max_price': 10.0}
[2] search_listings (via MCP)
      in:  {'description': 'graphic tee', 'size': 'XS', 'max_price': 10.0}
      out: [] (empty)
      →    branch: empty, working out what to tell the user, then stopping
[3] search_listings (via MCP)
      in:  {'description': 'graphic tee', 'size': None, 'max_price': None}
      out: 7 items: Graphic Tee — 2003 Tour Bootleg Style, Y2K Baby Tee — Butterfly Print, Vintage Band Tee — Faded Grey … +4 more
      →    re-search with a filter dropped, to see which one emptied it
[4] search_listings (via MCP)
      in:  {'description': 'graphic tee', 'size': None, 'max_price': 10.0}
      out: [] (empty)
      →    re-search with a filter dropped, to see which one emptied it
[5] search_listings (via MCP)
      in:  {'description': 'graphic tee', 'size': 'XS', 'max_price': None}
      out: [] (empty)
      →    re-search with a filter dropped, to see which one emptied it
[6] stop
      out: I couldn't find 'graphic tee' in size XS under $10. You could loosen both the size and the price. Nothing fits…
      →    suggest_outfit never called

  I couldn't find 'graphic tee' in size XS under $10. You could loosen both the size and the price. Nothing fits both, the closest thing is the Graphic Tee — 2003 Tour Bootleg Style in size L for $24.

0 model calls this session
```

The empty one never gets to `suggest_outfit`. It does 3 extra searches (all through MCP) to work out which filter emptied it, then stops at step 6 with 0 model calls.

**The three failure modes, triggered on purpose**

1. *Empty search.* `python app.py ask 'designer ballgown size XXS under $5'` stops before suggest_outfit and says: "Nothing in the listings matches 'designer ballgown' in size XXS under $5, and nothing matches 'designer ballgown' even with no size or price limit, so it's the words. Try naming the type of piece (tee, jacket, jeans, boots, cardigan) or a style (vintage, y2k, grunge, 90s)." This already worked from last unit, nothing to add.

2. *Empty wardrobe.* `python app.py ask 'denim jacket under $50' --empty-wardrobe` didn't crash and didn't come back empty, it gave general outfit ideas (wide-leg black trousers, floral slip dress...). This was also already handled in `suggest_outfit`. The one thing I changed after testing it (see How I Used AI) is that it now says up front that these are general ideas, because otherwise it looks like the app made up clothes you own:
   ```
   Outfit:   You don't have any wardrobe items saved, so these are general ideas, not pieces from your closet:
   Outfit 1: Pair it with high-waisted wide-leg black trousers, a simple white t-shirt, chunky loafers, and a minimalist leather tote bag.
   Outfit 2: Throw it over a floral midi slip dress with beat-up canvas sneakers and a nylon shoulder bag for a great nineties mix.
   ```

3. *Model unavailable.* I changed the last character of my key and ran a query I'd never asked before (`'corduroy pants under $40'`) so the cache couldn't answer it. Instead of editing `.env` and having to remember to put it back, I set the broken key just for that one command, `GEMINI_API_KEY=<key with last char changed> python app.py ask ...`, which wins over the `.env` value. Before I added a handler this is what happened:
   ```
   ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

   1 model calls this session
   ```
   No stack trace, but only because `app.py` catches everything at the very top. `run_agent` itself crashed, the program exited with code 1, and the listing it had already found was thrown away. A run in `run_eval.py` would've just been logged as CRASHED. So I added a handler in `run_agent` that catches `ModelUnavailable` around both model steps, puts a message in `session["error"]` and stops. Now it says:
   ```
   [3] suggest_outfit
         in:  new_item=lst_005
         out: ModelUnavailable
         →    model unreachable, stopping

     Found a match, the Corduroy Wide-Leg Pants — Rust ($32 on depop), but I couldn't reach the AI model to style it or write the fit card. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. Your search itself worked, so once that's fixed just run the same query again. (If someone else set this app up for you, this isn't something you did wrong - let them know the model key isn't working.)
   ```
   I also added a handler for `MCPError` around the search, since now that search goes through a separate server process that's a new way for it to break. That one tells you to run `python mcp_server.py` on its own to see the error.

**On the MCP move:** I moved `search_listings` since it's the one that doesn't call the model. In `mcp_server.py` I registered it with `@mcp.tool()` and wrote the description for someone who can't see my code (units on max_price, how size matching works, and that it returns `[]` when nothing matches). `python mcp_client.py` lists it with `description: string`, `size: string (optional)`, `max_price: number (optional)`, which matches my Tool Inventory. In `agent.py` I added a little `_search()` helper that calls `call_tool("search_listings", {...})` and swapped every search in `run_agent` over to it, including the extra searches the empty branch does to figure out which filter killed the results.

Did anything behave differently? Not that I could find. I ran `'graphic tee'` under $30 both ways and the MCP version gave back the exact same 7 listing dicts in the same order (`a == b` was True), and the empty search came back as a real `[]`, not a string or None, so the branch still works. The only difference is speed: each call starts the server up, which is about 0.25s, so the ballgown query (2 searches) takes about half a second now instead of being instant.

---

## The Improvement

**What I changed:** One line of the `create_fit_card` prompt in `tools.py`. It used to say:

```
- say the price exactly as $42 and the platform name 'poshmark', once each
```

Now it says:

```
- say the price exactly as $42 once and the platform name 'poshmark' once, but put them in DIFFERENT sentences. Don't write the usual 'snagged/found/got it on poshmark for $42' line, every thrift caption has that one
```

Nothing else changed: same search, same loop, same outfit prompt, same temperature, same scenarios. I didn't test the new wording a few times first to tune it, I just made the change and ran the whole thing (`python run_eval.py --label after`, 90 model calls, cache off). The log is [results/run_2026-10-11_2217_after.md](results/run_2026-10-11_2217_after.md).

**Which failure it was meant to fix:** the revised criterion 4 miss. My diagnosis was that asking for the price and the platform as a pair is what makes the model reach for "snagged it on poshmark for $42", so I split them up.

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Matching query completes all three tools and returns a fit card | 4 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 2. Impossible query stops before suggest_outfit, message names what to change | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 3. Same item id in search_results[0], selected_item, suggest_outfit and create_fit_card | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |
| 4. Fit card has exact price + platform and is 280 chars or less (and the 5 don't all open the same) | 4 of 5 | FAIL | PASS | PASS | PASS | PASS | MET (4/5) |
| 4 (revised). Same, plus no stock "snagged it on poshmark for $42" sentence | 4 of 5 | FAIL | PASS | FAIL | PASS | PASS | **MISSED (3/5)** |
| 5. Price ceiling parsed right and respected, 5 phrasings | 5 of 5 | PASS | PASS | PASS | PASS | PASS | MET (5/5) |

Side by side, just the rows that moved:

| | Before | After |
|---|---|---|
| 4. original | MET (5/5) | MET (4/5) |
| 4. revised | MISSED (1/5) | MISSED (3/5) |

And across all 45 fit cards in each run, not just criterion 4's query (counted with `check_run.py` plus a quick script over both logs):

| Across every card in the run | Before | After |
|---|---|---|
| Uses the stock "snagged/found/got it on X for $Y" sentence | 28/45 | 4/45 |
| Price and platform in the same sentence, any wording | 44/45 | 29/45 |
| Passes revised criterion 4 | 17/45 | 36/45 |
| Passes original criterion 4 (price + platform + 280 chars) | 45/45 | 40/45 |

The 5 cards that failed the original check after the change: two left out the platform ("Best $42 addition to my closet yet!" never says poshmark), one left out the price ("Scored this gem on depop and honestly haven't taken it off since"), and two went over 280 characters (294 and 298).

Criterion 4 try 1 after, the one that dropped the platform:
```
This light wash cropped denim jacket gives off such a cool streetwear vibe thrown over an oversized grey crewneck. I love how it looks with wide-leg khaki trousers and chunky boots. Best $42 addition to my closet yet! 🧥✨ #streetwear #thriftstyle #denimjacket
```
And try 4, which passes the revised one:
```
Cropped light wash denim is officially my new daily uniform. Paired it with a white tank and baggy jeans today. Score secured on poshmark for $42. 👖✨ #denimjacket #ootd #streetwear
```

**Did it help, and how do I know:** Partly. It did what it was aimed at: the stock sentence went from 28 of 45 cards to 4 of 45, and revised criterion 4 went from 1/5 to 3/5. But it still misses the 4 of 5 target, and it cost me something I didn't have a problem with before. Every card in the before run had the price and the platform and fit in 280 characters (45/45), and after the change 5 cards broke that (40/45), so the original criterion 4 dropped from 5/5 to 4/5. My guess is that splitting price and platform into separate sentences makes the caption longer, and gives the model a chance to forget one of them because they're not tied together anymore. So I traded a style problem for a small accuracy problem, and the accuracy one matters more to someone actually trying to buy the thing.

Also worth saying: try 4 above passes my regex but "Score secured on poshmark for $42" is pretty much the same sentence. My regex only knows six verbs. So 4/45 is probably a bit better than the truth.

---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
