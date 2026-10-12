# Notes from reading the data (Milestone 1)

Read through `python app.py listings --full -n 6` and then just skimmed all 40
with `python app.py listings -n 40`.

## Listing fields

`id`, `title`, `description`, `category`, `style_tags` (list), `size`,
`condition`, `price` (float), `colors` (list), `brand` (str or None), `platform`

The three I actually care about for search: **title / description / style_tags**
for the keywords, **size** for the size filter, **price** for the ceiling.

Stuff I noticed:

- `brand` is None on most of them. Only like 8 out of 40 have one (Levi's,
  Champion, Woolrich, Ralph Lauren...). Can't rely on it in a prompt.
- Sizes are all over the place. Tops are `S`, `M`, `L/XL`, `S/M`,
  `XL (oversized)`, `One Size / Oversized`. Pants are waist sizes like `W30 L30`
  or `W28`. Shoes are `US 7`, `US 8.5`. So "size M" and "size 8" mean totally
  different things depending on category. A plain `"m" in size` check would be
  a mess (`"s" in "us 9"` is True lol).
- `category` is one of tops / bottoms / outerwear / shoes / accessories. The
  silk slip dress (lst_013) is filed under bottoms, which is a little weird.
- Platforms: depop, thredUp, poshmark.
- Prices go from $12 (belt) to $75 (leather bomber). Most stuff is $15–$45.

## Wardrobe

A wardrobe is `{"items": [...]}`. Each item has `id`, `name`, `category`,
`colors`, `style_tags`, `notes` (can be null). The example one has 10 things in
it (baggy jeans, white tank, black combat boots, etc).

An empty wardrobe is just `{"items": []}` — same shape, empty list. So the
outfit tool has to check `len(wardrobe["items"]) == 0`, not whether the dict
exists.

## Starter run

```
$ python app.py ask 'vintage graphic tee under $30'

  The planning loop isn't built yet — see the TODO in agent.py.

0 model calls this session
```

That's the expected starting point, nothing is built yet.
