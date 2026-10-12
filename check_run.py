#!/usr/bin/env python3
"""
Score a run log from run_eval.py against MY five criteria (criteria.md).

    python check_run.py results/run_..._before.md

run_eval.py leaves the PASS/FAIL columns blank on purpose. I'd rather not
eyeball 50 tries, so this reads the report it wrote and applies each criterion
exactly the way it's worded in criteria.md. It prints every try with the reason
it passed or failed, so I can still check it by hand.

It only reads the report. It doesn't run the agent again.
"""

import re
import sys
from pathlib import Path

import scenarios as scenario_module


def parse_report(path: Path) -> dict:
    """{scenario name: [try dict, ...]} from the 'What actually happened' part."""
    text = path.read_text(encoding="utf-8")
    text = text.split("## What actually happened", 1)[1]
    out = {}
    for block in text.split("\n### ")[1:]:
        name, body = block.split("\n", 1)
        tries = []
        for chunk in re.split(r"\*\*Try \d+\*\*", body)[1:]:
            t = {"crashed": "Crashed:" in chunk, "error": None, "selected": None,
                 "selected_price": None, "platform": None, "fit_card": None,
                 "trace": ""}
            m = re.search(r"- stopped early: yes — (.*)", chunk)
            if m:
                t["error"] = m.group(1)
            m = re.search(r"- selected_item: (.*?) \(\$([\d.]+), (\w+)\)", chunk)
            if m:
                t["selected"], t["selected_price"], t["platform"] = (
                    m.group(1), float(m.group(2)), m.group(3))
            m = re.search(r"Fit card:\n\n```\n(.*?)\n```", chunk, re.S)
            if m:
                t["fit_card"] = m.group(1)
            m = re.search(r"Trace:\n\n```\n(.*)\n```", chunk, re.S)
            if m:
                t["trace"] = m.group(1)
            tries.append(t)
        out[name.strip()] = tries
    return out


def steps(trace: str) -> list[str]:
    """Each '[n] name ...' step of the trace as its own string."""
    return re.split(r"\n(?=\[\d+\] )", trace) if trace else []


def step_named(trace: str, name: str) -> list[str]:
    return [s for s in steps(trace) if re.match(rf"\[\d+\] {re.escape(name)}", s)]


# ── one function per criterion. Each returns (passed, reason) ────────────────

def c1(t, scenario):
    if t["crashed"]:
        return False, "crashed"
    if t["error"]:
        return False, f"stopped early: {t['error'][:70]}"
    got = [n for n in ("search_listings", "suggest_outfit", "create_fit_card")
           if step_named(t["trace"], n)]
    if len(got) < 3:
        return False, f"only ran {got}"
    if not (t["fit_card"] or "").strip():
        return False, "no fit card"
    return True, "3 tools ran, fit card returned"


def c2(t, scenario):
    if t["crashed"]:
        return False, "crashed"
    if not t["error"]:
        return False, "didn't stop"
    if step_named(t["trace"], "suggest_outfit"):
        return False, "suggest_outfit was called"
    names_a_change = any(w in t["error"].lower() for w in ("size", "budget", "price", "words"))
    if not names_a_change:
        return False, f"message doesn't name what to change: {t['error'][:70]}"
    return True, "stopped before suggest_outfit, message names what to change"


def c3(t, scenario):
    if t["crashed"] or t["error"]:
        return False, "didn't get past search"
    search = step_named(t["trace"], "search_listings")
    # some titles have commas in them ("Light Wash, Cropped"), so check that the
    # list STARTS with the selected title instead of splitting on commas
    first_ok = f"items: {t['selected']}" in search[0]
    selected_id = re.search(r"selected_item = (\w+)", search[0]).group(1)
    outfit_id = re.search(r"new_item=(\w+)", step_named(t["trace"], "suggest_outfit")[0]).group(1)
    card_id = re.search(r"new_item=(\w+)", step_named(t["trace"], "create_fit_card")[0]).group(1)
    ids = {selected_id, outfit_id, card_id}
    if not first_ok:
        return False, f"search_results[0] isn't selected_item '{t['selected']}'"
    if len(ids) != 1:
        return False, f"ids differ: selected={selected_id} outfit={outfit_id} card={card_id}"
    return True, f"{selected_id} everywhere (search[0] = selected = outfit = card)"


def c4(t, scenario):
    if t["crashed"] or t["error"] or not t["fit_card"]:
        return False, "no fit card"
    card = t["fit_card"]
    price = t["selected_price"]
    dollars = f"{price:.0f}" if price.is_integer() else f"{price:.2f}"
    problems = []
    if not re.search(rf"\${re.escape(dollars)}(\.00)?(?!\d)", card):
        problems.append(f"no ${dollars}")
    if t["platform"].lower() not in card.lower():
        problems.append(f"no '{t['platform']}'")
    if len(card) > 280:
        problems.append(f"{len(card)} chars")
    if problems:
        return False, ", ".join(problems)
    return True, f"has ${dollars} + {t['platform']}, {len(card)} chars"


def c5(t, scenario):
    if t["crashed"]:
        return False, "crashed"
    want = float(scenario["expect_max_price"])
    parse = step_named(t["trace"], "parse_query")[0]
    m = re.search(r"'max_price': ([\d.]+|None)", parse)
    parsed = None if m.group(1) == "None" else float(m.group(1))
    if parsed != want:
        return False, f"max_price parsed as {parsed}, wanted {want:g}"
    search = step_named(t["trace"], "search_listings")[0]
    m = re.search(r"prices \$([\d.]+)-\$([\d.]+)", search)
    if not m:
        return True, f"max_price={parsed:g}, search came back empty (nothing over it)"
    top = float(m.group(2))
    if top > want:
        return False, f"result priced ${top:g} is over ${want:g}"
    return True, f"max_price={parsed:g}, results ${m.group(1)}-${top:g}"


CHECKS = {1: c1, 2: c2, 3: c3, 4: c4, 5: c5}


def opening(card: str) -> str:
    return " ".join(re.findall(r"\S+", card)[:5]).lower()


def main():
    path = Path(sys.argv[1])
    report = parse_report(path)
    by_name = {s["name"]: s for s in scenario_module.SCENARIOS}

    for name, tries in report.items():
        scenario = by_name.get(name)
        number = scenario.get("criterion") if scenario else None
        print(f"\n{name}  (criterion {number})")
        if number is None:
            for i, t in enumerate(tries, 1):
                state = "crashed" if t["crashed"] else ("stopped" if t["error"] else "completed")
                print(f"  try {i}: {state}")
            continue
        results = []
        for i, t in enumerate(tries, 1):
            ok, why = CHECKS[number](t, scenario)
            results.append(ok)
            print(f"  try {i}: {'PASS' if ok else 'FAIL'}  {why}")
        print(f"  -> {sum(results)}/{len(results)}  row: "
              + " | ".join("PASS" if r else "FAIL" for r in results))
        if number == 4:
            openings = [opening(t["fit_card"] or "") for t in tries]
            same = len(set(openings)) == 1
            print(f"  openings ({'ALL THE SAME - fails' if same else 'not all the same - ok'}):")
            for o in openings:
                print(f"     {o}")


if __name__ == "__main__":
    main()
