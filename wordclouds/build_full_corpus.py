"""Build the full-corpus word-cloud input: the 263 papers plus PubMed papers that mention SIMD only in their full text.

simd_papers_full.csv lists every paper with the search that found it:
  title_abstract  - simd_papers.csv (SIMD in title or abstract, plus the original list)
  full_text       - open-access PubMed papers whose full text mentions "Scottish Index of Multiple
                    Deprivation" (Europe PMC, 14 October 2026), excluding conference abstract books,
                    papers citing SIMD only in their references, and records without body text
Titles and abstracts are fetched from Europe PMC into data/ (ignored by git) and checked against the
SHA-256 fingerprints in simd_papers_full.csv, as prepare_corpus.py does for the 263-paper corpus.

  python wordclouds/build_full_corpus.py --init   # once: create simd_papers_full.csv from epmc_text/_manifest.csv
  python wordclouds/build_full_corpus.py          # fetch, check and write data/simd_full_corpus.csv
  python wordclouds/generate.py --settings wordclouds/settings_full.json \
      --input data/simd_full_corpus.csv --output-dir wordclouds/outputs_full
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_corpus import BATCH, ROOT, fetch  # noqa: E402
from prepare_corpus import plain, sha256  # noqa: E402

PAPERS = ROOT / "simd_papers_full.csv"
RECORDS = ROOT / "data" / "europe_pmc_records_full.json"
CORPUS = ROOT / "data" / "simd_full_corpus.csv"
COLUMNS = ["Year", "PMID", "DOI", "Title", "Found_by", "Title_SHA256", "Abstract_SHA256"]


def fetch_records(pmids):
    """Europe PMC MED records for these PMIDs, cached in data/."""
    if RECORDS.exists():
        cached = json.loads(RECORDS.read_text())
        if set(pmids) <= {r["pmid"] for r in cached["records"]}:
            return cached
    records = {}
    for start in range(0, len(pmids), BATCH):
        for record in fetch(pmids[start:start + BATCH]):
            if record.get("source") == "MED" and record.get("pmid") in pmids:
                records[record["pmid"]] = record
        print(f"{len(records)}/{len(pmids)} records", flush=True)
    missing = sorted(set(pmids) - records.keys(), key=int)
    if missing:
        raise SystemExit(f"Europe PMC returned no record for: {', '.join(missing)}")
    fetched = {"fetched": time.strftime("%Y-%m-%d"), "records": [records[p] for p in sorted(records, key=int)]}
    RECORDS.parent.mkdir(exist_ok=True)
    RECORDS.write_text(json.dumps(fetched, ensure_ascii=False, indent=1) + "\n")
    return fetched


def init():
    """Create simd_papers_full.csv from simd_papers.csv and the Europe PMC full-text manifest."""
    papers = [{"PMID": r["PMID"], "Found_by": "title_abstract"}
              for r in csv.DictReader((ROOT / "simd_papers.csv").open(encoding="utf-8"))]
    known = {p["PMID"] for p in papers}
    manifest = csv.DictReader((ROOT / "epmc_text" / "_manifest.csv").open(encoding="utf-8"))
    papers += [{"PMID": r["pmid"], "Found_by": "full_text"} for r in manifest
               if r["use_for_extraction"] == "yes" and r["pmid"] not in known]
    records = {r["pmid"]: r for r in fetch_records([p["PMID"] for p in papers])["records"]}
    rows = []
    for p in papers:
        r = records[p["PMID"]]
        rows.append({"Year": r["pubYear"], "PMID": p["PMID"], "DOI": r.get("doi", ""), "Title": plain(r["title"]),
                     "Found_by": p["Found_by"], "Title_SHA256": sha256(plain(r["title"])),
                     "Abstract_SHA256": sha256(plain(r.get("abstractText", "")))})
    rows.sort(key=lambda r: (int(r["Year"]), int(r["PMID"])))
    with PAPERS.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {PAPERS.name}: {len(rows)} papers")


def build(allow_changes):
    papers = list(csv.DictReader(PAPERS.open(encoding="utf-8")))
    records = {r["pmid"]: r for r in fetch_records([p["PMID"] for p in papers])["records"]}
    rows, changed = [], []
    for p in papers:
        r = records[p["PMID"]]
        title, abstract = plain(r["title"]), plain(r.get("abstractText", ""))
        if (sha256(title), sha256(abstract)) != (p["Title_SHA256"], p["Abstract_SHA256"]):
            changed.append(p["PMID"])
        rows.append({"Year": r["pubYear"], "PMID": p["PMID"], "Title": title, "Abstract": abstract,
                     "Found_by": p["Found_by"]})
    if changed and not allow_changes:
        raise SystemExit(f"{len(changed)} records differ from simd_papers_full.csv: {', '.join(changed[:20])}. "
                         "Rerun with --allow-changes to build from the current records.")
    with CORPUS.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    no_abstract = sum(not r["Abstract"] for r in rows)
    print(f"{len(rows)} papers ({no_abstract} without an abstract); wrote {CORPUS.relative_to(ROOT)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--init", action="store_true", help="create simd_papers_full.csv (needs epmc_text/_manifest.csv)")
    parser.add_argument("--allow-changes", action="store_true", help="build even if records differ from the fingerprints")
    args = parser.parse_args()
    init() if args.init else build(args.allow_changes)
