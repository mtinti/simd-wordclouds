"""Download the indexed records for every PMID in simd_papers.csv from Europe PMC.

The abstracts are not redistributed in this repository. This script fetches them
from the free Europe PMC REST API into data/ (ignored by git). Then run
prepare_corpus.py, which checks every record against the published fingerprints.

Run: python wordclouds/fetch_corpus.py
"""
import csv
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
BATCH = 50


def fetch(pmids):
    query = f"EXT_ID:({' OR '.join(pmids)}) AND SRC:MED"
    params = urllib.parse.urlencode({"query": query, "resultType": "core", "format": "json", "pageSize": 1000})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(f"{API}?{params}", timeout=60) as response:
                return json.load(response)["resultList"]["result"]
        except OSError:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def main():
    with (ROOT / "simd_papers.csv").open(encoding="utf-8", newline="") as f:
        pmids = [row["PMID"] for row in csv.DictReader(f)]
    records = {}
    for start in range(0, len(pmids), BATCH):
        for record in fetch(pmids[start:start + BATCH]):
            if record.get("source") == "MED" and record.get("pmid") in pmids:
                records[record["pmid"]] = record
        print(f"{len(records)}/{len(pmids)} records")
    missing = sorted(set(pmids) - records.keys(), key=int)
    if missing:
        raise SystemExit(f"Europe PMC returned no record for: {', '.join(missing)}")
    out = ROOT / "data" / "europe_pmc_records.json"
    out.parent.mkdir(exist_ok=True)
    fetched = {"fetched": time.strftime("%Y-%m-%d"), "records": [records[p] for p in sorted(records, key=int)]}
    out.write_text(json.dumps(fetched, ensure_ascii=False, indent=1) + "\n")
    print(f"Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
