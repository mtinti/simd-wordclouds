"""Build the word-cloud corpus from the paper list and the downloaded Europe PMC records.

Run fetch_corpus.py first. Every title and abstract is checked against the SHA-256
fingerprints in simd_papers.csv, taken from the 4 October 2026 snapshot that the
published images were made from. Any difference stops the build unless
--allow-changes is given; the differences are then listed in data_audit.json.

Writes data/simd_263_papers_year_pmid_abstract.csv (ignored by git, because the
abstracts are not redistributed) and wordclouds/data_audit.json.
"""
import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
PAPERS = ROOT / "simd_papers.csv"
RECORDS = ROOT / "data" / "europe_pmc_records.json"
CORPUS = ROOT / "data" / "simd_263_papers_year_pmid_abstract.csv"
ORIGINAL = ROOT / "simd_252_papers_year_pmid_abstract.csv"


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-changes", action="store_true",
                        help="build even if records differ from the published fingerprints")
    args = parser.parse_args()
    if not RECORDS.exists():
        raise SystemExit("No downloaded records. Run: python wordclouds/fetch_corpus.py")
    papers = list(csv.DictReader(PAPERS.open(encoding="utf-8", newline="")))
    fetched = json.loads(RECORDS.read_text())
    records = {r["pmid"]: r for r in fetched["records"]}
    assert len({p["PMID"] for p in papers}) == len(papers), "PMIDs must be unique"
    rows, changed = [], []
    for paper in papers:
        pmid = paper["PMID"]
        record = records[pmid]
        assert record["source"] == "MED" and record["id"] == pmid
        title, abstract = plain(record["title"]), plain(record.get("abstractText", ""))
        assert title and abstract, f"Missing indexed text: {pmid}"
        differences = [name for name, text, expected in [("title", title, paper["Title_SHA256"]),
                                                         ("abstract", abstract, paper["Abstract_SHA256"])]
                       if sha256(text) != expected]
        if record["pubYear"] != paper["Year"]:
            differences.append("year")
        if differences:
            changed.append({"PMID": pmid, "changed": differences})
        rows.append({
            "Year": record["pubYear"], "PMID": pmid, "Title": title, "Abstract": abstract,
            "PDF_Status": paper["PDF_Status"], "Abstract_Source": paper["Abstract_Source"],
            "Added_from_missing_list": paper["Added_from_missing_list"],
        })
    if changed and not args.allow_changes:
        listing = "; ".join(f"{c['PMID']} ({', '.join(c['changed'])})" for c in changed)
        raise SystemExit(f"{len(changed)} records differ from the published snapshot: {listing}. "
                         "Rerun with --allow-changes to build from the current records.")
    rows.sort(key=lambda r: (int(r["Year"]), int(r["PMID"])))
    CORPUS.parent.mkdir(exist_ok=True)
    with CORPUS.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    original = list(csv.DictReader(ORIGINAL.open(encoding="utf-8-sig", newline="")))
    audit = {
        "paper_list": PAPERS.name, "paper_list_sha256": sha256(PAPERS.read_text(encoding="utf-8")),
        "papers": len(rows), "added_from_missing_list": sum(r["Added_from_missing_list"] == "yes" for r in rows),
        "snapshot_date": "2026-10-04", "records_fetched": fetched["fetched"],
        "records_matching_snapshot": len(rows) - len(changed), "records_differing_from_snapshot": changed,
        "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
        "original_file": ORIGINAL.name, "original_sha256": hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
        "template_abstracts_in_original": sum(r["Abstract"].startswith("Study examining ") for r in original),
        "notes": [
            "Abstracts are not redistributed: fetch_corpus.py downloads them from Europe PMC by PMID.",
            "Title and abstract SHA-256 fingerprints in simd_papers.csv come from the 4 October 2026 snapshot used for the published images.",
            "The original 252-paper CSV is kept unchanged; its abstracts were title-derived template sentences.",
            "in_user_downloaded_list follows the user's CSV; it is not a fresh audit of the original PDFs.",
        ],
    }
    (HERE / "data_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(rows)} papers; {len(rows) - len(changed)} match the published snapshot; wrote {CORPUS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
