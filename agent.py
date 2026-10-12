"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import suggest_outfit, create_fit_card
from generate import ModelUnavailable
from mcp_client import call_tool, MCPError


def _search(description, size, max_price) -> list[dict]:
    """search_listings, but through the MCP server instead of a direct call.
    Every search in the agent goes through here (unit 4, Milestone 1)."""
    return call_tool("search_listings", {
        "description": description,
        "size": size,
        "max_price": max_price,
    })


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        "tool_calls": [],            # every tool call, in order, with the item id it got
    }


# ── query parsing ─────────────────────────────────────────────────────────────

# "under $30", "below 30", "max $25", "less than $40", "up to 50"
_PRICE_BEFORE = re.compile(
    r"\b(?:under|below|less than|max(?:imum)?|up to|no more than)\s*\$?\s*(\d+(?:\.\d+)?)(?:\s*dollars)?",
    re.I,
)
# "$20 or less", "30 dollars max", "$40 or under"
_PRICE_AFTER = re.compile(
    r"\$?(\d+(?:\.\d+)?)\s*(?:dollars\s*)?(?:or less|or under|or below|max)\b",
    re.I,
)
# a bare "$30" with nothing around it - I'm treating that as a ceiling too
_PRICE_BARE = re.compile(r"\$\s*(\d+(?:\.\d+)?)")

# "size M", "in size 8", "size W30", "size 8.5", "size XXS"
_SIZE = re.compile(r"(?:\bin\s+)?\bsize\s+(w?\d+(?:\.\d+)?|[a-z]{1,4})\b", re.I)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max_price out of what the user typed.
    Plain regex, no model call. Whatever's left after taking out the price and
    size is the description.
    """
    text = query
    max_price = None

    for pattern in (_PRICE_BEFORE, _PRICE_AFTER, _PRICE_BARE):
        match = pattern.search(text)
        if match:
            max_price = float(match.group(1))
            text = text[: match.start()] + " " + text[match.end():]
            break

    size = None
    match = _SIZE.search(text)
    if match:
        size = match.group(1).upper()
        text = text[: match.start()] + " " + text[match.end():]

    description = re.sub(r"[,;]", " ", text)
    description = re.sub(r"\s+", " ", description).strip()
    return {"description": description, "size": size, "max_price": max_price}


def _no_results_message(parsed: dict, session: dict) -> str:
    """
    The search came back empty. Work out WHICH part of the request did it, by
    searching again with each filter taken off, so the message can say what to
    change instead of just "no results".
    """
    desc, size, max_price = parsed["description"], parsed["size"], parsed["max_price"]

    if not desc:
        return (
            "I couldn't tell what kind of item you want. Add what you're looking "
            "for, like 'graphic tee', 'denim jacket' or 'platform sneakers'."
        )

    def relaxed(size_, price_):
        results = _search(desc, size_, price_)
        trace.step(
            "search_listings (via MCP)",
            inputs=str({"description": desc, "size": size_, "max_price": price_}),
            returned=results,
            note="re-search with a filter dropped, to see which one emptied it",
        )
        session["tool_calls"].append({
            "tool": "search_listings",
            "inputs": {"description": desc, "size": size_, "max_price": price_},
            "result_count": len(results),
            "why": "checking which filter emptied the search",
        })
        return results

    asked = f"'{desc}'"
    if size:
        asked += f" in size {size}"
    if max_price is not None:
        asked += f" under ${max_price:g}"

    no_filters = relaxed(None, None) if (size or max_price is not None) else []
    if not no_filters:
        return (
            f"Nothing in the listings matches {asked}, and nothing matches "
            f"'{desc}' even with no size or price limit, so it's the words. "
            "Try naming the type of piece (tee, jacket, jeans, boots, cardigan) "
            "or a style (vintage, y2k, grunge, 90s)."
        )

    tips = []
    if size:
        without_size = relaxed(None, max_price)
        if without_size:
            sizes = sorted({r["size"] for r in without_size})[:4]
            tips.append(
                f"drop the size: there's {len(without_size)} match(es) in other "
                f"sizes ({', '.join(sizes)})"
            )
    if max_price is not None:
        without_price = relaxed(size, None)
        if without_price:
            cheapest = min(r["price"] for r in without_price)
            tips.append(
                f"raise your budget to ${cheapest:g}: that's the cheapest "
                f"match{' in your size' if size else ''}"
            )
    if not tips:
        best = no_filters[0]
        tips.append(
            "loosen both the size and the price. Nothing fits both, the "
            f"closest thing is the {best['title']} in size {best['size']} for "
            f"${best['price']:g}"
        )

    return f"I couldn't find {asked}. You could " + ", or ".join(tips) + "."


def _model_down_message(item: dict, exc: Exception) -> str:
    """The search worked but the model didn't. Say both, so the user knows
    their query was fine and it's the connection/key that needs fixing."""
    return (
        f"Found a match, the {item['title']} (${item['price']:g} on "
        f"{item['platform']}), but I couldn't reach the AI model to style it or "
        f"write the fit card. {exc} Your search itself worked, so once that's "
        "fixed just run the same query again. (If someone else set this app up "
        "for you, this isn't something you did wrong - let them know the model "
        "key isn't working.)"
    )


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)

    # The loop: each pass does one step, then looks at what that step put in
    # the session to decide the next one. None means stop.
    next_step = "parse"
    count = 0

    while next_step is not None:
        count += 1
        trace.check_iterations(count)

        if next_step == "parse":
            session["parsed"] = parse_query(session["query"])
            trace.step("parse_query", inputs=session["query"], returned=str(session["parsed"]))
            next_step = "search"

        elif next_step == "search":
            parsed = session["parsed"]
            try:
                results = _search(
                    parsed["description"],
                    parsed["size"],
                    parsed["max_price"],
                )
            except MCPError as exc:
                session["error"] = (
                    "The search server (mcp_server.py) couldn't be reached, so "
                    "nothing got searched. Run `python mcp_server.py` on its own "
                    "to see what's wrong with it, then ask again. "
                    f"Details: {str(exc).splitlines()[0]}"
                )
                trace.step("search_listings (via MCP)", inputs=str(parsed),
                           returned="MCPError", note="server failed, stopping")
                next_step = None
                continue
            session["search_results"] = results
            session["tool_calls"].append({
                "tool": "search_listings",
                "inputs": dict(parsed),
                "result_count": len(results),
            })

            # THE BRANCH. Empty search -> say what to change and stop, the
            # outfit tool never sees an empty item.
            if not session["search_results"]:
                trace.step("search_listings (via MCP)", inputs=str(parsed), returned=results,
                           note="branch: empty, working out what to tell the user, then stopping")
                session["error"] = _no_results_message(parsed, session)
                trace.step("stop", returned=session["error"], note="suggest_outfit never called")
                next_step = None
            else:
                session["selected_item"] = session["search_results"][0]
                trace.step("search_listings (via MCP)", inputs=str(parsed), returned=results,
                           note=f"branch: {len(results)} results (prices ${min(r['price'] for r in results):g}"
                                f"-${max(r['price'] for r in results):g}), selected_item = "
                                f"{session['selected_item']['id']}, going to suggest_outfit")
                next_step = "outfit"

        elif next_step == "outfit":
            item = session["selected_item"]
            try:
                session["outfit_suggestion"] = suggest_outfit(item, session["wardrobe"])
            except ModelUnavailable as exc:
                session["error"] = _model_down_message(item, exc)
                trace.step("suggest_outfit", inputs=f"new_item={item['id']}",
                           returned="ModelUnavailable", note="model unreachable, stopping")
                next_step = None
                continue
            wardrobe_size = len(session["wardrobe"].get("items", []))
            session["tool_calls"].append({
                "tool": "suggest_outfit",
                "item_id": item["id"],
                "wardrobe_size": wardrobe_size,
            })
            trace.step("suggest_outfit",
                       inputs=f"new_item={item['id']} ({item['title']}), wardrobe={wardrobe_size} items",
                       returned=session["outfit_suggestion"])
            next_step = "fit_card"

        elif next_step == "fit_card":
            item = session["selected_item"]
            try:
                session["fit_card"] = create_fit_card(session["outfit_suggestion"], item)
            except ModelUnavailable as exc:
                session["error"] = _model_down_message(item, exc)
                trace.step("create_fit_card", inputs=f"new_item={item['id']}",
                           returned="ModelUnavailable", note="model unreachable, stopping")
                next_step = None
                continue
            session["tool_calls"].append({
                "tool": "create_fit_card",
                "item_id": item["id"],
            })
            trace.step("create_fit_card",
                       inputs=f"new_item={item['id']}, outfit=<from suggest_outfit>",
                       returned=session["fit_card"], note="done")
            next_step = None

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
