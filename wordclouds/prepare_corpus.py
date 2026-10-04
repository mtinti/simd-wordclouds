"""Prepare indexed bibliographic text from the archived Europe PMC records.

Preserves the user's original CSV. Writes corpus.json, data_audit.json and the
corrected 263-paper and 11-paper CSVs in the project root.
"""
import csv
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "simd_252_papers_year_pmid_abstract.csv"


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value)).split())


def main():
    original = list(csv.DictReader(SOURCE.open(encoding="utf-8-sig", newline="")))
    original_ids = {r["PMID"] for r in original}
    assert len(original) == len(original_ids) == 252
    missing = set((ROOT / "simd_pmids_not_downloaded.txt").read_text().split())
    assert not original_ids & missing
    records, sources = {}, {}
    inputs = {}
    for name in ["europe_pmc_search", "supplemental", "original_other_metadata"]:
        path = ROOT / f"research/{name}_2026-10-04.json"
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for row in json.loads(path.read_text())["resultList"]["result"]:
            records[row["pmid"]] = row
            sources[row["pmid"]] = str(path.relative_to(ROOT))
    target_ids = original_ids | missing
    assert target_ids <= records.keys()
    rows = []
    for pmid in sorted(target_ids, key=lambda p: (int(records[p]["pubYear"]), int(p))):
        record = records[pmid]
        assert record["source"] == "MED" and record["id"] == pmid
        title, abstract = plain(record["title"]), plain(record.get("abstractText", ""))
        assert title and abstract, f"Missing indexed text: {pmid}"
        rows.append({
            "Year": record["pubYear"], "PMID": pmid, "Title": title, "Abstract": abstract,
            "PDF_Status": "missing" if pmid in missing else "in_user_downloaded_list",
            "Abstract_Source": f"https://europepmc.org/article/MED/{pmid}",
            "Added_from_missing_list": "yes" if pmid in missing else "no",
        })
    audit = {
        "original_file": SOURCE.name,
        "original_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "original_rows": len(original), "final_rows": len(rows),
        "added_pmids": sorted(missing, key=int),
        "template_abstracts_in_original": sum(r["Abstract"].startswith("Study examining ") for r in original),
        "titles_differing_from_indexed_record": sum(r["Title"] != plain(records[r["PMID"]]["title"]) for r in original),
        "abstracts_replaced_in_corrected_copy": len(original),
        "abstracts_available": sum(bool(r["Abstract"]) for r in rows),
        "metadata_snapshot_date": "2026-10-04", "metadata_sha256": inputs,
        "source_file_by_pmid": {p: sources[p] for p in sorted(target_ids, key=int)},
        "notes": [
            "Original CSV preserved byte-for-byte. Its 252 abstracts were title-derived template sentences.",
            "Corrected copy uses indexed titles, publication years and actual abstracts for every PMID.",
            "in_user_downloaded_list follows the user's CSV; it is not a fresh audit of their original 123 PDFs.",
            "11 missing-PDF papers are included equally. Two publications without PMIDs are outside this 263-PMID corpus.",
        ],
    }
    (HERE / "corpus.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    for filename, selected in [("simd_263_papers_year_pmid_abstract.csv", rows),
                               ("simd_missing_fulltext_abstracts.csv", [r for r in rows if r["PDF_Status"] == "missing"])]:
        with (ROOT / filename).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL, lineterminator="\n")
            writer.writeheader()
            writer.writerows(selected)
    (HERE / "data_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in audit.items() if not isinstance(v, (dict, list))}, indent=2))


if __name__ == "__main__":
    main()
