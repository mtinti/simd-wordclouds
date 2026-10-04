# SIMD title and abstract word clouds

Open **[outputs/index.html](outputs/index.html)** in your browser to see both clouds. Use the PNGs for slides and documents; the SVGs stay sharp when enlarged and contain the font. Both images are 3288 × 2220 pixels, tagged at 300 dpi.

The current vocabulary uses refined phrase pairings: **deprivation**, **socioeconomic status** and **inequality** remain distinct families. Read the [pairing review](pairing_refinement_report.md) for the decisions and resulting paper counts. Previous rules and images are preserved in `versions/before_pairing_refinement/`.

This uses the free, MIT-licensed [Python wordcloud package](https://github.com/amueller/word_cloud), with a bundled, openly licensed DejaVu Sans font. No paid software or online word-cloud service is required. The CSV rules can be edited in a text editor or a spreadsheet application. Rendering runs locally.

## The data correction matters

The supplied `simd_252_papers_year_pmid_abstract.csv` contains 252 unique PMIDs, but all 252 abstract fields are the same sentence template filled with each title. Some titles are also truncated. They are not the indexed article abstracts. Making an abstract cloud from those sentences would mainly measure the template.

The original file is preserved byte-for-byte. The corrected **[263-paper CSV](../simd_263_papers_year_pmid_abstract.csv)** uses the full indexed titles and abstracts from the archived Europe PMC MED records, matched by exact PMID. It includes the 11 records in the missing-PDF list. The **[11-paper CSV](../simd_missing_fulltext_abstracts.csv)** contains just those added records and their actual abstracts.

Source links, PDF status and a flag identifying the 11 additions accompany each row. Publication years follow the indexed metadata. `PDF_Status=in_user_downloaded_list` reflects your supplied 252-paper list, rather than a new inspection of the original 123 PDFs. All 263 rows have nonempty indexed titles and abstracts. The two references without PMIDs are outside this corpus. The metadata snapshot is dated 4 October 2026; `data_audit.json` records input hashes and provenance.

## How terms are counted

1. Analyse titles and abstracts separately, using all 263 PMIDs in both.
2. Normalize case, HTML entities, accents, possessives and punctuation. Hyphens and spaces are treated consistently. Numbers are retained while matching named phrases such as **type 1 diabetes**, then standalone numbers and unmapped one/two-character fragments are discarded.
3. Match the longest enabled phrase or alias against the original token sequence, without crossing sentence or section punctuation. A phrase consumes its words once: **colorectal cancer** does not also contribute a separate **cancer** occurrence. Do not interpret the count for “cancer” as the number of papers about all cancers. Explicitly labelled concept-family mappings may combine related terms; they are not assertions that different measures are interchangeable.
4. Apply the explicit exclusions to the resulting terms. Phrase matching precedes stopword removal, so **quality of life** is preserved and removing intervening words never creates a new phrase. No automatic stemming, hidden stopword library, automatic collocations or inferred synonym model is used.
5. By default, count **papers mentioning a term**, once per paper. This reduces the influence of repeated wording within a long abstract. Total mention counts are also exported. Longer abstracts can still mention more different concepts; paper frequency does not eliminate every length effect.
6. Keep terms occurring in at least 2 titles or 5 abstracts. Display up to 75 title terms and 95 abstract terms. Resolve equal counts alphabetically. Font sizes reflect frequency and layout fitting; use the frequency table for exact comparisons. Font scales are fitted independently for each cloud, so do not compare physical sizes across clouds.

Colours are decorative, chosen by a stable hash of each term so the same term has the same colour in both images. They do not encode a clinical category, effect direction or significance.

These clouds describe vocabulary. They do not measure study quality, effect sizes, whether deprivation increases or decreases an outcome, or the absence of a topic from the full texts. Generic comparison words are excluded, so the images must not be used to infer the direction of findings. Titles and abstracts can emphasize different aspects of the same paper.

## Review and change the vocabulary

Use **[the searchable rules page](outputs/review_terms.html)** for review. It is read-only; make edits in the CSV files, then rerun the script.

| File | What to review or change |
| --- | --- |
| [term_groups.csv](term_groups.csv) | Canonical display term; variants separated by `|`; kind of mapping; enabled flag; reason. `1` enables a rule and `0` disables it. |
| [exclusions.csv](exclusions.csv) | Excluded term or phrase; category; enabled flag; reason. `1` excludes it and `0` retains it unless another active rule excludes the same canonical term. |
| [settings.json](settings.json) | Seed, count method, colours, minimum paper counts, term limits, canvas and font sizes. |
| [term_frequencies.csv](outputs/term_frequencies.csv) | Paper counts, mention counts, percentage, exclusion reason and whether each term appears in the image. |
| [observed_term_variants.csv](outputs/observed_term_variants.csv) | Observed token forms, their mapped terms and occurrence counts, separately by title/abstract. |
| [terms_by_paper.csv](outputs/terms_by_paper.csv) | Retained terms for every PMID, allowing checks against individual papers. |

The current choices distinguish exact variants, concept families and ambiguous fragments:

- **Grouped:** `tumor/tumour`; `hospitalization/hospitalisation`; `children/child`; `healthcare/health care`; `SIMD/Scottish Index of Multiple Deprivation`; documented clinical abbreviations.
- **Grouped as a deprivation family:** generic, socioeconomic, social and area-based deprivation, deprivation status, deprived and socioeconomically deprived. This is an explicit topic grouping for the cloud. It does not equate individual and area-level measures or distinguish most-deprived from least-deprived groups. The original forms remain in the variant audit.
- **Grouped as a status/position family:** socioeconomic status, socioeconomic position, SES and SEP. Standalone socioeconomic is not assigned to this family. Explicit socioeconomic factors, circumstances, backgrounds, gradients and differences retain their nouns.
- **Kept separate:** deprivation versus socioeconomic status versus inequality; health versus socioeconomic inequality; type 1 and type 2 diabetes; named cancer sites; death and mortality.
- **Protected status phrases:** health status, smoking status, vaccination status, performance status, medication status and other explicit qualifiers. Standalone status and socioeconomic are excluded as incomplete phrases.
- **Not expanded:** CHD, because it can refer to coronary heart disease or congenital hand differences in this collection. It is excluded as ambiguous.
- **Excluded by default:** grammatical words, abstract headings, generic study/statistical wording, calendar terms, SIMD and Scottish geographic context. Geographic/index exclusions create a topic-focused view; switch their flags to `0` if that context should appear.
- **Retained by default:** substantive terms including deprivation, health, age, sex, rural, urban, risk, mortality and survival. Their frequency is part of the corpus. The exclusion file has disabled entries for several of these, making optional further exclusions explicit.

The proposed all-in-one “Socioeconomic conditions” umbrella is disabled in `term_groups.csv`. A topic grouping is not necessarily a synonym. To enable it, first disable any conflicting existing mappings; the script refuses ambiguous enabled aliases rather than silently choosing one. Count and review the revised frequencies before interpreting the result. A merged family is counted only once per paper, even when that paper uses several of its aliases.

## Reproduce the images

Python 3.12 is recommended. From the project root, create a local environment once:

```sh
python3.12 -m venv .venv-wordcloud
.venv-wordcloud/bin/python -m pip install -r wordclouds/requirements.txt
```

Then regenerate after any rule or setting change:

```sh
.venv-wordcloud/bin/python wordclouds/generate.py
```

This workspace already has the environment configured. On Windows, use `.venv-wordcloud\Scripts\python.exe` instead of `.venv-wordcloud/bin/python`.

The input defaults to the corrected 263-paper CSV. To use a different CSV with `Year`, `PMID`, `Title` and `Abstract` columns:

```sh
.venv-wordcloud/bin/python wordclouds/generate.py --input my_papers.csv --output-dir wordclouds/my_outputs
```

The script refuses the known template abstracts and duplicate PMIDs. It writes a run manifest with the seed, package versions, all analysis input hashes and output hashes. The seed is `20261004`. Output sorting, font file, colour assignments and rendering settings are fixed. No timestamp is inserted into the images. `requirements.txt` pins the package versions used here; the font is included with its licence. Identical reruns in the tested environment produce byte-identical PNGs, SVGs and CSVs. Exact pixel identity on another platform also depends on its font-rendering libraries; compare the manifest and supplied images when reproducing elsewhere.

To verify the term-processing safeguards:

```sh
.venv-wordcloud/bin/python wordclouds/test_processing.py
```

`reproducibility_check.json` records the comparison between two complete runs with different Python hash seeds. Both cloud formats, the frequency tables and HTML review pages are compared by SHA-256. Eleven processing checks cover phrase boundaries, ambiguous qualifiers, subtype preservation and grouping behaviour. The indexed data and original CSV preservation were checked separately.

## Files to share

- `outputs/titles_wordcloud.png` and `outputs/abstracts_wordcloud.png`: high-resolution images.
- Corresponding `.svg` files: scalable versions with the exact font embedded.
- `outputs/term_frequencies.csv`, the two rule CSVs and `settings.json`: the reviewable analysis choices and exact counts.
- `generate.py`, `requirements.txt` and `assets/`: the portable generation code and rendering inputs.

The vocabulary choices are a first reviewable version. Common useful revisions are retaining Scottish places, collapsing selected related concepts after review, or showing only clinical topics. Each changes the question the cloud answers, so keep the rules and frequency table with any shared figure.
