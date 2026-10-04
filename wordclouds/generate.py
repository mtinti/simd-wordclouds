"""Deterministic, locally generated SIMD word clouds; no online services needed.

Run: python wordclouds/generate.py
Edit term_groups.csv, exclusions.csv and settings.json to revise the analysis.
"""
import argparse
import base64
from collections import Counter
import csv
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import unicodedata
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
os.environ.setdefault("MPLCONFIGDIR", str(HERE / ".cache"))
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from wordcloud import WordCloud


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, columns):
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def tokens(text, keep_boundaries=False):
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\b([a-z]+)'s\b", r"\1", text)
    if keep_boundaries:
        text = re.sub(r"[.!?;:,()\[\]\r\n]+", " | ", text)
    return re.findall(r"[a-z]+[a-z0-9]*|[0-9]+" + (r"|\|" if keep_boundaries else ""), text)


class Rules:
    """Term rules. With `phrases` settings, process() counts multi-word phrases instead of words."""

    def __init__(self, groups, exclusions, phrases=None):
        self.phrases = phrases
        self.aliases = {}
        self.exclusions = {}
        self.categories = {}
        self.exclusion_phrases = {}
        skip = set(phrases["skip_group_canonicals"]) if phrases else set()
        for row in groups:
            if row["enabled"] != "1" or row["canonical"] in skip:
                continue
            canonical = row["canonical"]
            for alias in [canonical, *row["variants"].split("|")]:
                key = tuple(tokens(alias))
                if key in self.aliases and self.aliases[key] != canonical:
                    raise ValueError(f"Conflicting enabled mappings for {alias!r}. Disable the old mapping first.")
                self.aliases[key] = canonical
        for row in exclusions:
            if row["enabled"] != "1":
                continue
            key = tuple(tokens(row["term"]))
            canonical = self.aliases.get(key, row["term"])
            self.exclusions[canonical.lower()] = row["reason"]
            self.categories[canonical.lower()] = row["category"]
            if len(key) > 1:  # single words need no matching, so plural merging still applies to them
                self.exclusion_phrases[key] = canonical
        self.max_length = max(map(len, [*self.aliases, *self.exclusion_phrases]), default=1)
        self.plurals = {}

    def fold_plurals(self, vocabulary, exceptions=()):
        """Map regular plurals of unmapped words to a singular form observed in the corpus."""
        for word in vocabulary:
            if (word,) in self.aliases or word in exceptions or len(word) < 4:
                continue
            if word.endswith("ies") and word[:-3] + "y" in vocabulary:
                singular = word[:-3] + "y"
            elif word.endswith("s") and not word.endswith(("ss", "us", "is")) and word[:-1] in vocabulary:
                singular = word[:-1]
            else:
                continue
            singular = self.aliases.get((singular,), singular)
            # Never let an excluded plural reappear under a retained singular.
            if word not in self.exclusions or singular.lower() in self.exclusions:
                self.plurals[word] = singular

    def units(self, text):
        """Yield (canonical, surface, mapped) for each matched unit, or None at a boundary or dropped fragment."""
        words = tokens(text, keep_boundaries=True)
        i = 0
        while i < len(words):
            if words[i] == "|":
                yield None
                i += 1
                continue
            # Match before stopword removal so no artificial phrases bridge removed words.
            for length in range(min(self.max_length, len(words) - i), 0, -1):
                key = tuple(words[i:i + length])
                canonical = self.aliases.get(key, self.exclusion_phrases.get(key))
                if canonical is not None:
                    mapped = True
                    break
            else:
                length, canonical, mapped = 1, self.plurals.get(words[i], words[i]), False
            surface = " ".join(words[i:i + length])
            i += length
            # Numbers and one/two-character unmapped fragments have no useful cloud meaning.
            if (length == 1 and surface not in ("uk",) and len(canonical) < 3) or canonical.isdigit():
                yield None
                continue
            yield canonical, surface, mapped

    def process(self, text):
        """Return term counts and (observed form, term) counts for one text."""
        if self.phrases:
            return self.process_phrases(text)
        counts, variants = Counter(), Counter()
        for unit in self.units(text):
            if unit:
                canonical, surface, _ = unit
                counts[canonical] += 1
                variants[(surface, canonical)] += 1
        return counts, variants

    def process_phrases(self, text):
        """Count runs of adjacent units with at least two words and at least one non-excluded unit.

        Grammar and other `break_categories` end a run, as do punctuation, numbers and fragments,
        so phrases never bridge removed words. Other excluded units (e.g. 'area', 'quintile') may
        appear inside a phrase to give context but cannot form a phrase alone.
        """
        breaks = set(self.phrases["break_categories"])
        counts, variants = Counter(), Counter()
        runs, run = [], []
        for unit in [*self.units(text), None]:
            if unit is None or self.categories.get(unit[0].lower()) in breaks:
                runs.append(run)
                run = []
            else:
                run.append(unit)
        for run in runs:
            for n in range(1, self.phrases["max_units"] + 1):
                for start in range(len(run) - n + 1):
                    window = run[start:start + n]
                    if sum(len(c.split()) for c, _, _ in window) < 2:
                        continue
                    if all(c.lower() in self.exclusions for c, _, _ in window):
                        continue
                    key = " ".join(c for c, _, _ in window)
                    # Show mapped units by their canonical name and everything else as written.
                    shown = " ".join(c if mapped else s for c, s, mapped in window)
                    counts[key] += 1
                    variants[(shown, key)] += 1
        return counts, variants


def count_terms(rules, texts):
    """Total mentions, and papers mentioning each term (once per paper however often repeated)."""
    mentions, papers, variants, by_paper = Counter(), Counter(), Counter(), []
    for text in texts:
        counts, seen = rules.process(text)
        mentions.update(counts)
        papers.update(counts.keys())
        variants.update(seen)
        by_paper.append(counts)
    return mentions, papers, variants, by_paper


def select_terms(weight, eligible, limit):
    """Order terms by weight, then name; never split a tie at the display limit."""
    ordered = sorted(eligible, key=lambda t: (-weight[t], t.casefold(), t))
    if len(ordered) > limit:
        boundary = weight[ordered[limit]]
        ordered = [t for t in ordered[:limit] if weight[t] > boundary]
    return ordered


def fold_subphrases(papers, eligible, ratio):
    """Map a phrase to a longer eligible phrase containing it that covers at least `ratio` of its papers."""
    folded = {}
    for short in eligible:
        padded = f" {short} "
        longer = [t for t in eligible if len(t) > len(short) and padded in f" {t} " and papers[t] >= ratio * papers[short]]
        if longer:
            folded[short] = min(longer, key=lambda t: (-papers[t], t))
    return folded


def display_labels(variants):
    """Label each phrase with its most frequent displayed form (ties: alphabetical)."""
    labels = {}
    for (shown, key), count in sorted(variants.items(), key=lambda item: (-item[1], item[0])):
        labels.setdefault(key, shown)
    if len(set(labels.values())) != len(labels):
        labels = {key: key for key in labels}
    return labels


def colour_for(term, palette):
    return palette[int(hashlib.sha256(term.encode()).hexdigest()[:8], 16) % len(palette)]


def write_review(groups, exclusions, out):
    sections = []
    for title, rows in [("Term groups and preserved phrases", groups), ("Exclusions", exclusions)]:
        columns = list(rows[0])
        header = ''.join(f'<th>{html.escape(k.replace("_", " "))}</th>' for k in columns)
        body = ''.join('<tr>' + ''.join(f'<td>{html.escape(row[k])}</td>' for k in columns) + '</tr>' for row in rows)
        sections.append(f'<h2>{title}</h2><p>{len(rows)} rules. Enabled: 1 = active; 0 = proposed or retained.</p><div class="table"><table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table></div>')
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Review SIMD term rules</title><style>body{margin:40px auto;max-width:1400px;padding:0 25px;font:16px/1.5 system-ui;background:#faf9f6;color:#153f4a}h1{font-size:36px}a{color:#176b73}input{padding:12px;width:min(90%,550px);font:inherit}.table{overflow:auto;max-height:650px}table{border-collapse:collapse;width:100%}td,th{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid #d6dedb}th{position:sticky;top:0;background:#e9efec}tr:nth-child(even){background:#f1f3f0}</style><h1>Review the word-cloud vocabulary</h1><p><a href="index.html">Back to the clouds</a>. These tables display the rules used for the images. Edit <a href="../term_groups.csv">term_groups.csv</a> or <a href="../exclusions.csv">exclusions.csv</a> and rerun the Python script to apply changes. This page is a read-only review.</p><input id="search" placeholder="Filter terms or reasons, e.g. deprivation" aria-label="Filter rule tables">' + ''.join(sections) + '<script>document.querySelector("#search").addEventListener("input",e=>{const q=e.target.value.toLowerCase();document.querySelectorAll("tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script></html>\n'
    (out / "review_terms.html").write_text(document)


def shape_mask(settings, field):
    """Mask for word placement: 0 inside the shape (inset by padding), 255 outside."""
    shape = settings["shape"]
    if field not in shape["fields"]:
        return None
    image = Image.new("L", (settings["width"], settings["height"]), 255)
    draw = ImageDraw.Draw(image)
    pad = shape["padding"]
    for cx, cy, rx, ry in shape["ellipses"]:
        draw.ellipse((cx - rx + pad, cy - ry + pad, cx + rx - pad, cy + ry - pad), fill=0)
    for x, y, w, h, r in shape["rounded_rects"]:
        draw.rounded_rectangle((x + pad, y + pad, x + w - pad, y + h - pad), radius=r - pad, fill=0)
    return np.array(image)


def render_cloud(field, frequencies, rows, settings, out):
    font = HERE / settings["font_file"]
    colour = lambda word, **kwargs: colour_for(word, settings["palette"])
    shape = settings["shape"]
    shaped = field in shape["fields"]
    cloud = WordCloud(
        width=settings["width"], height=settings["height"], scale=settings["scale"], mask=shape_mask(settings, field),
        font_path=str(font), random_state=settings["seed"],
        background_color=None if shaped else settings["background"], mode="RGBA" if shaped else "RGB",
        color_func=colour, max_words=len(frequencies), margin=9,
        prefer_horizontal=1.0, min_font_size=settings["min_font_size"],
        max_font_size=settings["max_font_size"], relative_scaling=settings["relative_scaling"],
        collocations=False, normalize_plurals=False, repeat=False,
    ).generate_from_frequencies(frequencies)
    label = "titles" if field == "Title" else "abstracts"
    unit = "phrases" if settings["phrases"]["enabled"] else "terms"
    title = f"{'Phrases' if unit == 'phrases' else 'Themes'} in paper {label}"
    years = [int(r["Year"]) for r in rows]
    count = sum(bool(r[field].strip()) for r in rows)
    subtitle = f"{count} papers  /  {min(years)}–{max(years)}  /  Scottish Index of Multiple Deprivation literature"
    metric = "paper prevalence" if settings["frequency"] == "papers" else "total term mentions"
    footer = (f"Size reflects {metric}. Adjacent multi-word phrases; phrases do not cross grammar words or punctuation."
              if unit == "phrases" else f"Size reflects {metric}. Reviewed term groups; common wording excluded.")
    footer2 = f"{len(cloud.layout_)} {unit} shown  /  Full counts and editable rules accompany these images"
    width, height = settings["width"] + 144, settings["height"] + 260
    scale = settings["scale"]
    canvas = Image.new("RGB", (width * scale, height * scale), settings["background"])
    draw = ImageDraw.Draw(canvas)

    def text(x, y, value, size, fill):
        draw.text((x * scale, y * scale), value, font=ImageFont.truetype(str(font), size * scale), fill=fill)

    text(72, 30, "SIMD LITERATURE", 16, "#176B73")
    text(72, 58, title, 43, "#153F4A")
    text(72, 119, subtitle, 17, "#52646A")
    if shaped:
        for cx, cy, rx, ry in shape["ellipses"]:
            draw.ellipse(((72 + cx - rx) * scale, (161 + cy - ry) * scale, (72 + cx + rx) * scale, (161 + cy + ry) * scale), fill=shape["fill"])
        for x, y, w, h, r in shape["rounded_rects"]:
            draw.rounded_rectangle(((72 + x) * scale, (161 + y) * scale, (72 + x + w) * scale, (161 + y + h) * scale), radius=r * scale, fill=shape["fill"])
        words = cloud.to_image()
        canvas.paste(words, (72 * scale, 161 * scale), words)
    else:
        canvas.paste(cloud.to_image(), (72 * scale, 161 * scale))
    line_y = height - 81
    draw.line((72 * scale, line_y * scale, (width - 72) * scale, line_y * scale), fill="#D6DEDB", width=scale)
    text(72, height - 62, footer, 16, "#52646A")
    text(72, height - 37, footer2, 14, "#52646A")
    canvas.save(out / f"{label}_wordcloud.png", dpi=(300, 300), optimize=False)

    # Embed the exact full font bytes for portable SVGs; avoid timestamped font subsetting.
    ns = "http://www.w3.org/2000/svg"
    ET.register_namespace("", ns)
    tag = lambda name: f"{{{ns}}}{name}"
    svg = ET.Element(tag("svg"), width=str(width), height=str(height), viewBox=f"0 0 {width} {height}")
    ET.SubElement(svg, tag("title")).text = title
    ET.SubElement(svg, tag("desc")).text = subtitle + ". " + footer
    style = ET.SubElement(svg, tag("style"))
    encoded = base64.b64encode(font.read_bytes()).decode()
    style.text = f"@font-face{{font-family:'DejaVu Sans';src:url(data:font/ttf;base64,{encoded}) format('truetype');}}text{{font-family:'DejaVu Sans';}}"
    ET.SubElement(svg, tag("rect"), width="100%", height="100%", fill=settings["background"])

    def svg_text(x, y, value, size, fill):
        element = ET.SubElement(svg, tag("text"), x=str(x), y=str(y), fill=fill, **{"font-size": str(size)})
        element.text = value

    svg_text(72, 46, "SIMD LITERATURE", 16, "#176B73")
    svg_text(72, 99, title, 43, "#153F4A")
    svg_text(72, 135, subtitle, 17, "#52646A")
    if shaped:
        for cx, cy, rx, ry in shape["ellipses"]:
            ET.SubElement(svg, tag("ellipse"), cx=str(72 + cx), cy=str(161 + cy), rx=str(rx), ry=str(ry), fill=shape["fill"])
        for x, y, w, h, r in shape["rounded_rects"]:
            ET.SubElement(svg, tag("rect"), x=str(72 + x), y=str(161 + y), width=str(w), height=str(h), rx=str(r), fill=shape["fill"])
    nested = ET.fromstring(cloud.to_svg(embed_font=False))
    # to_svg honours scale; use its viewBox to place it at the same logical dimensions.
    nested.set("viewBox", f"0 0 {settings['width'] * scale} {settings['height'] * scale}")
    nested.set("width", str(settings["width"]))
    nested.set("height", str(settings["height"]))
    nested.set("x", "72")
    nested.set("y", "161")
    svg.append(nested)
    ET.SubElement(svg, tag("line"), x1="72", y1=str(line_y), x2=str(width - 72), y2=str(line_y), stroke="#D6DEDB")
    svg_text(72, height - 47, footer, 16, "#52646A")
    svg_text(72, height - 22, footer2, 14, "#52646A")
    (out / f"{label}_wordcloud.svg").write_text(ET.tostring(svg, encoding="unicode") + "\n")
    return {word for (word, frequency), *rest in cloud.layout_}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "simd_263_papers_year_pmid_abstract.csv")
    parser.add_argument("--output-dir", type=Path, default=HERE / "outputs")
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    settings = json.loads((HERE / "settings.json").read_text())
    if settings["frequency"] not in ("papers", "mentions"):
        raise ValueError('frequency must be "papers" or "mentions"')
    rows = read_csv(args.input)
    assert rows and len({r["PMID"] for r in rows}) == len(rows), "PMIDs must be unique"
    rows.sort(key=lambda r: int(r["PMID"]))
    if any(r["Abstract"].startswith("Study examining ") and "evaluating health data linkage" in r["Abstract"] for r in rows):
        raise ValueError("Template abstracts detected. Use the corrected indexed corpus.")
    groups, excluded = read_csv(HERE / "term_groups.csv"), read_csv(HERE / "exclusions.csv")
    phrase_mode = settings["phrases"]["enabled"]
    rules = Rules(groups, excluded, settings["phrases"] if phrase_mode else None)
    vocabulary = Counter(w for row in rows for field in ["Title", "Abstract"] for w in tokens(row[field]))
    if settings["merge_plurals"]:
        rules.fold_plurals(vocabulary, set(settings["plural_exceptions"]))
    audit, usages, per_paper, summary = [], [], [], {}
    for field in ["Title", "Abstract"]:
        mentions, papers, variants, by_paper = count_terms(rules, [row[field] for row in rows])
        for row, counts in zip(rows, by_paper):
            retained = sorted(t for t in counts if t.lower() not in rules.exclusions)
            per_paper.append({"PMID": row["PMID"], "source": field, "retained_terms": " | ".join(retained)})
        eligible = [t for t in papers if papers[t] >= settings["minimum_papers"][field] and t.lower() not in rules.exclusions]
        folded = fold_subphrases(papers, eligible, settings["phrases"]["fold_into_longer"]) if phrase_mode else {}
        eligible = [t for t in eligible if t not in folded]
        labels = display_labels(variants) if phrase_mode else {t: t for t in papers}
        weight = papers if settings["frequency"] == "papers" else mentions
        ordered = select_terms(weight, eligible, settings["maximum_terms"][field])
        frequencies = {labels[t]: weight[t] for t in ordered}
        if not frequencies:
            raise ValueError(f"No terms remaining in {field}; review the exclusions and thresholds")
        shown_labels = render_cloud(field, frequencies, rows, settings, out)
        shown = {t for t in ordered if labels[t] in shown_labels}
        if len(shown) < len(frequencies):
            print(f"Warning: {field} cloud fits only {len(shown)} of {len(frequencies)} terms; enlarge the canvas or reduce the limit.")
        for term in sorted(papers, key=lambda t: (-papers[t], t.casefold(), t)):
            reason = rules.exclusions.get(term.lower(), "")
            if term in folded:
                reason = f"Mostly within the longer phrase '{folded[term]}'"
            record = {"source": field, "term": term, "paper_count": papers[term], "mention_count": mentions[term],
                      "paper_percent": f"{100 * papers[term] / len(rows):.2f}", "excluded": "yes" if reason else "no",
                      "exclusion_reason": reason, "shown": "yes" if term in shown else "no"}
            if phrase_mode:
                record["displayed_as"] = labels[term]
            audit.append(record)
        for (surface, canonical), count in sorted(variants.items()):
            usages.append({"source": field, "observed_form": surface, "canonical_term": canonical, "mentions": count})
        summary[field] = {"papers_with_text": sum(bool(r[field].strip()) for r in rows), "eligible_terms": len(eligible),
                          "displayed_terms": len(shown),
                          "lowest_displayed_count": min(frequencies.values()), "top_terms": [{"term": labels[t], "papers": papers[t]} for t in ordered[:15]]}
    write_csv(out / "term_frequencies.csv", audit, list(audit[0]))
    write_csv(out / "observed_term_variants.csv", usages, list(usages[0]))
    write_csv(out / "terms_by_paper.csv", per_paper, list(per_paper[0]))
    plural_rows = [{"plural": p, "merged_into": s, "plural_tokens": vocabulary[p], "singular_tokens": vocabulary.get(s, 0)}
                   for p, s in sorted(rules.plurals.items())]
    write_csv(out / "plural_merges.csv", plural_rows, ["plural", "merged_into", "plural_tokens", "singular_tokens"])
    images = "\n".join(f'<section><h2>{name.title()}</h2><a href="{name}_wordcloud.svg"><img src="{name}_wordcloud.png" alt="Word cloud from paper {name}"></a><p><a href="{name}_wordcloud.png">PNG, 300 dpi</a> · <a href="{name}_wordcloud.svg">Scalable SVG</a></p></section>' for name in ["titles", "abstracts"])
    (out / "index.html").write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>SIMD word clouds</title><style>body{max-width:1200px;margin:40px auto;padding:0 24px;background:#faf9f6;color:#153f4a;font:18px/1.55 system-ui}h1{font-size:40px}img{width:100%;height:auto}a{color:#176b73}section{margin:40px 0;border-top:1px solid #d6dedb}p{max-width:950px}</style><h1>SIMD literature word clouds</h1><p>' + str(len(rows)) + ' indexed titles and abstracts, including papers with missing PDFs. Term size reflects ' + ('the number of papers mentioning the term' if settings['frequency'] == 'papers' else 'the total number of term mentions') + '. Colours are decorative and consistent between the clouds.</p><p><a href="review_terms.html">Browse and search all term rules</a> · <a href="../exclusions.csv">Review exclusions</a> · <a href="term_frequencies.csv">Review exact frequencies</a> · <a href="../README.md">Method and rerun instructions</a></p>' + images + '</html>\n')
    write_review(groups, excluded, out)
    inputs = {"corpus": digest(args.input)}
    for name in ["settings.json", "term_groups.csv", "exclusions.csv", "generate.py", settings["font_file"]]:
        inputs[name] = digest(HERE / name)
    outputs = {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name != "run_manifest.json"}
    manifest = {"seed": settings["seed"], "papers": len(rows), "frequency": settings["frequency"], "summary": summary,
                "python": platform.python_version(), "packages": {p: importlib.metadata.version(p) for p in ["wordcloud", "numpy", "Pillow", "matplotlib"]},
                "input_sha256": inputs, "output_sha256": outputs}
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
