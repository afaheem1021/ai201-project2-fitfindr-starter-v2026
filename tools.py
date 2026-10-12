"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# Words that show up in how people ask for things but say nothing about the
# item. Without this, "looking for a tee" scores a point on every listing whose
# description happens to contain "a".
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "in", "on", "of", "with", "to",
    "i", "im", "i'm", "me", "my", "want", "need", "looking", "find", "some",
    "something", "any", "that", "is", "it", "size", "under", "below", "max",
    "less", "than", "around", "about", "please", "cheap",
}

LETTER_SIZES = {"XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"}


def _words(text: str) -> list[str]:
    """Lowercase words with punctuation stripped, and a plain plural strip so
    'sneakers' and 'sneaker' count as the same word."""
    words = []
    for w in re.findall(r"[a-z0-9']+", text.lower()):
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        words.append(w)
    return words


def _size_tokens(size: str) -> set[str]:
    """'XL (oversized)' -> {'XL', 'OVERSIZED'}, 'W30 L30' -> {'W30', 'L30'}."""
    return {t for t in re.split(r"[/\s(),]+", size.upper()) if t}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    My size rule (it's written in the README too):
      - the wanted size has to equal one whole token of the listing's size,
        so 'M' matches 'S/M' and 'M/L' but never 'XL'
      - numbers ignore a 'US' or 'W' in front, so '8' matches 'US 8' (not
        'US 8.5') and '30' matches 'W30 L30'
      - 'One Size' listings fit any letter size, but not a shoe or waist size
    """
    wanted = wanted.strip().upper()
    if not wanted:
        return True
    tokens = _size_tokens(listing_size)

    if wanted in tokens:
        return True

    # strip a W / US prefix off both sides and compare the numbers
    number = re.sub(r"^(US|W)", "", wanted)
    if re.fullmatch(r"\d+(\.\d+)?", number):
        listing_numbers = {re.sub(r"^W", "", t) for t in tokens}
        return number in listing_numbers

    if wanted in LETTER_SIZES and "ONE" in tokens and "SIZE" in tokens:
        return True

    return False


def _score(listing: dict, keywords: list[str]) -> int:
    """Title and style tags are worth 2 a hit, everything else 1. If the whole
    phrase shows up in the title in order, that's 3 more - otherwise 'graphic
    tee' ties between the actual Graphic Tee and a baby tee with a print."""
    strong = set(_words(listing["title"] + " " + " ".join(listing["style_tags"])))
    weak = set(_words(
        listing["description"] + " " + " ".join(listing["colors"]) + " " + listing["category"]
    ))
    score = 0
    for word in keywords:
        if word in strong:
            score += 2
        elif word in weak:
            score += 1
    if len(keywords) > 1 and " ".join(keywords) in " ".join(_words(listing["title"])):
        score += 3
    return score


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = [w for w in _words(description or "") if w not in STOPWORDS]
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue
        score = _score(listing, keywords)
        if score > 0:
            scored.append((score, listing))

    # sort() is stable, so ties keep the order they have in the file
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    if not new_item:
        return ""

    item_text = _describe_item(new_item)
    items = (wardrobe or {}).get("items") or []

    system = (
        "You're a friendly stylist who's really into thrifting. Keep it short "
        "and practical. Plain text, no markdown headers, no bold."
    )

    if not items:
        # empty wardrobe: nothing of theirs to name, so give general advice
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
            "They haven't told us what's in their closet. Give 2 outfit ideas "
            "for this piece, describing the kinds of pieces that would go with "
            "it (type of bottoms/top, shoes, maybe one accessory). One line "
            "each, starting with 'Outfit 1:' and 'Outfit 2:'. Reply with only "
            "those two lines, no intro."
        )
    else:
        closet = "\n".join(
            f"- {w['name']} ({w['category']}; colors: {', '.join(w['colors'])}"
            + (f"; note: {w['notes']}" if w.get("notes") else "")
            + ")"
            for w in items
        )
        prompt = (
            f"Someone is thinking about buying this thrifted item:\n{item_text}\n\n"
            f"Here's what they already own:\n{closet}\n\n"
            "Give 2 outfits that pair the new item with pieces from their closet. "
            "Only use pieces from the list above and call them by the name "
            "they're listed under. One line each, starting with 'Outfit 1:' and "
            "'Outfit 2:'. Reply with only those two lines, no intro."
        )

    response = generate(prompt, system=system).strip()
    if response and not items:
        # found in unit 4: with no note, the user can't tell why the outfits
        # name clothes they don't own
        response = (
            "You don't have any wardrobe items saved, so these are general "
            "ideas, not pieces from your closet:\n" + response
        )
    if not response:
        # the model has come back empty on me once or twice; don't pass "" on
        return f"Wear the {new_item.get('title', 'piece')} with simple basics and let it be the focus."
    return response


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return "Can't make a fit card yet - there's no outfit to build it from."

    price = _format_price(new_item["price"])
    prompt = (
        f"Write a caption for a social media post about this thrift find.\n\n"
        f"Item: {new_item['title']}\n"
        f"Price: {price}\n"
        f"Found on: {new_item['platform']}\n"
        f"Condition: {new_item['condition']}\n"
        f"How I'm styling it: {outfit.strip()}\n\n"
        "Rules:\n"
        "- 2 to 4 short sentences, under 280 characters total\n"
        # unit 4 improvement: price and platform in the SAME sentence is what
        # produced "snagged it on depop for just $24" on 28 of 45 cards
        f"- say the price exactly as {price} once and the platform name "
        f"'{new_item['platform']}' once, but put them in DIFFERENT sentences. "
        f"Don't write the usual 'snagged/found/got it on {new_item['platform']} "
        f"for {price}' line, every thrift caption has that one\n"
        "- sound like a real person posting their fit, casual, not like a "
        "product description\n"
        "- pick ONE outfit from the styling notes, don't list both\n"
        "- at most 2 emojis and 3 hashtags, and don't hashtag the platform\n"
        "- don't open with 'Scored', 'Just thrifted' or 'Obsessed' - start "
        "with something specific to this piece or this outfit\n"
        "Only reply with the caption itself."
    )
    return generate(prompt).strip()


def _format_price(price: float) -> str:
    """24.0 -> '$24', 24.5 -> '$24.50'."""
    return f"${price:.0f}" if float(price).is_integer() else f"${price:.2f}"


def _describe_item(item: dict) -> str:
    """The listing as a few lines of text for a prompt. Brand is left out when
    it's None, which is most of the time - otherwise the model gets told the
    brand is 'None'."""
    lines = [
        f"{item['title']} ({item['category']})",
        f"Colors: {', '.join(item.get('colors', []))}",
        f"Style: {', '.join(item.get('style_tags', []))}",
        f"Size: {item.get('size')}, condition: {item.get('condition')}",
        f"Description: {item.get('description', '')}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)
