# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
My search is just keyword matching, no synonyms. Somebody who types "t-shirt"
when the listing says "tee", or "sneaks" for sneakers, is going to get nothing
back even though the item is right there. Two of the three calls also go to the
model, and a rate limit hiccup or an empty response could break a run. So I
think 1 miss out of 5 is honest. I didn't go lower than 4 because the example
queries were literally checked against the data, so if they fail more than once
something is actually broken.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path doesn't touch the model at all. It's a plain `if not results:` in
my code, so it should either work every time or never. There's no randomness
in it, so anything less than 5 of 5 means the branch is broken, not unlucky.
"Names what to change" means the message mentions at least one of the price,
the size, or the search words, not just "No results".

---

## 3. The item search found is the item the other two tools get

For a query that matches, `session["selected_item"]["id"]` is the same as
`session["search_results"][0]["id"]`, AND the same id shows up as the item
logged for both `suggest_outfit` and `create_fit_card` in
`session["tool_calls"]` — 5 of 5 tries. I'll check it with a little script that
prints the four ids side by side; they all have to be identical.

**Why this target:**
Same as criterion 2, there's no model involved in passing the item along, it's
just reading a dict out of the session. If the ids ever don't match, that's a
bug in my loop (like grabbing the wrong index or a stale variable), not
randomness, so I'm not giving it any slack. I log the ids in `tool_calls`
because otherwise I'd only be checking that the session field exists, not that
the tool really received it.

---

## 4. The fit card reads like a real post

Run the same matching query 5 times with the cache off. A fit card counts as
good if all of these are true: it contains the item's exact price written like
`$24` (or `$24.00`), it contains the platform name (depop / thredUp / poshmark,
case doesn't matter), and it's 280 characters or less (so it'd fit in a tweet).
At least 4 of the 5 cards have to pass. On top of that, the 5 cards can't all
start with the same first 5 words.

**Why this target:**
The model writes these at temperature 0.9 so the wording will be different
every time, which is fine, I don't care about the exact words. What I care
about is that it doesn't forget the two facts that make it useful (price and
where to buy it) and doesn't turn into a paragraph. I'm allowing 1 miss because
models sometimes just drop a detail or ramble even when the prompt says not to.
The "not the same first 5 words" part is there so I'd notice if it turned into
a template.

> **Revised in unit 4:** Same run (one query, 5 times, cache off), same 4 of 5
> target. A card passes if it has the exact price, the platform name, is 280
> characters or less, AND it doesn't use the stock "[snagged / found / got /
> copped / scored / grabbed] it on [platform] for $[price]" sentence. I check
> that last part with a regex in `check_run.py::uses_stock_sentence`: one of
> those verbs, then "on <platform>" within 40 characters, then a `$` price
> within 15 more, all in the same sentence.
>
> **Why revised:** my reason above says the first-5-words check is there to
> catch the cards turning into a template. They did turn into a template, just
> not at the start. In the before run 4 of the 5 cards for this query had
> "Found this gem on poshmark for only $42" / "Snagged it on poshmark for $42"
> in the middle, and across every scenario it was 28 of 45 cards. The opening
> check passed all of them because it was looking in the wrong place, so it
> measured the wrong thing. The original line above stays as it was, and I
> scored both versions.

---

## 5. The price ceiling actually gets respected

I'll run 5 queries that each say the price a different way:
`'graphic tee under $30'`, `'denim jacket below 50'`, `'cardigan max $40'`,
`'platform sneakers less than $60'`, `'band tee $20 or less'`. For every one,
`session["parsed"]["max_price"]` has to be the number I typed, and every
listing in `session["search_results"]` has to have a price at or under it.
5 of 5 queries.

**Why this target:**
The scary failure here is a silent one: if my regex doesn't catch a phrasing,
max_price ends up None and the search just ignores the budget with no error.
That's the same thing as the PowerShell `$30` problem in the instructions. The
filter itself is a simple `<=`, so once the price is parsed it can't really be
wrong, which is why it's 5 of 5. The part that can fail is the parsing, which
is why I test five different ways of saying it instead of the same query five
times.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
