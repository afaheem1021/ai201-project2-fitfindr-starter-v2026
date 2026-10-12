"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # Criterion 1: a query the data can match should get all three tools
        # and a fit card.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # Criterion 2: the branch. Nothing can match this, it should stop
        # before suggest_outfit with a message that names what to change.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # Criterion 3: state. A different matching query than criterion 1 so
        # I'm not only checking one item. What I check is that the same id
        # shows up as search_results[0], selected_item, and the item handed to
        # suggest_outfit and create_fit_card (it's in the trace).
        "name": "same item reaches every tool",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 4: the fit card. Same query five times, cache off. Each
        # card needs the exact price ($42), the platform (poshmark) and to be
        # 280 chars or less, and the 5 can't all open with the same 5 words.
        "name": "fit card has price + platform, <= 280 chars",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 4,
    },
    # Criterion 5: five different ways of saying a price. My criterion is one
    # try per phrasing (5 phrasings = the 5 tries), so in the README table
    # Try N is phrasing N. run_eval runs each of these 5 times anyway - the
    # parsing and filtering don't involve the model, so all 5 runs of one
    # phrasing should agree, and if they don't that's a finding too.
    {
        "name": "price ceiling: 'under $30'",
        "query": "graphic tee under $30",
        "wardrobe": "example",
        "criterion": 5,
        "expect_max_price": 30,
    },
    {
        "name": "price ceiling: 'below 50'",
        "query": "denim jacket below 50",
        "wardrobe": "example",
        "criterion": 5,
        "expect_max_price": 50,
    },
    {
        "name": "price ceiling: 'max $40'",
        "query": "cardigan max $40",
        "wardrobe": "example",
        "criterion": 5,
        "expect_max_price": 40,
    },
    {
        "name": "price ceiling: 'less than $60'",
        "query": "platform sneakers less than $60",
        "wardrobe": "example",
        "criterion": 5,
        "expect_max_price": 60,
    },
    {
        "name": "price ceiling: '$20 or less'",
        "query": "band tee $20 or less",
        "wardrobe": "example",
        "criterion": 5,
        "expect_max_price": 20,
    },
    {
        # Not one of my five. Unit 4's empty-wardrobe failure mode, kept in so
        # I can see it doesn't crash or come back empty across 5 runs.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
