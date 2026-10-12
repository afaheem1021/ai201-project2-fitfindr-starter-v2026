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

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



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
