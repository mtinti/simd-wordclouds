# SIMD literature word clouds

What do studies that use the **Scottish Index of Multiple Deprivation (SIMD)** write about? This repository turns the titles and abstracts of 263 indexed papers (2005–2026) into reproducible, reviewable word clouds.

![Phrases in the titles of 263 SIMD papers, drawn inside a cloud outline. The largest are socioeconomic deprivation, socioeconomic status and socioeconomic inequality, followed by area deprivation, social deprivation and risk factor.](wordclouds/outputs/titles_wordcloud.png)

The cloud counts **multi-word phrases**, so deprivation appears in the context it was studied: *socioeconomic*, *area* and *social* deprivation stay separate rather than collapsing into one word. In the title cloud above, phrase size and shade both show how many papers use the phrase in their title. Each paper counts once, however often it repeats the phrase.

The same method applied to the full abstracts gives a richer picture: 68 phrases, each found in at least 5 abstracts. It keeps a rectangular layout because that many phrases do not fit inside the cloud outline at a readable size.

![Phrases in the abstracts of 263 SIMD papers. The largest are deprived areas, socioeconomic deprivation and socioeconomic status, followed by health care, risk factors, area deprivation, health inequality, primary care and hospital admission.](wordclouds/outputs/abstracts_wordcloud.png)

## Reading the cloud

- **Vocabulary, not findings.** The cloud shows what papers name in their titles. It does not show effect sizes, study quality or the direction of any association.
- **Phrases only.** A phrase is 2–3 adjacent words within a sentence. Grammar words, statistical and study-design wording, geography, deprivation-index names and data sources end a phrase, so "mortality and deprivation" or "most deprived SIMD quintile" never become phrases.
- **Ties are never split.** The title cloud shows the 25 phrases found in 3 or more titles. The 55 phrases found in exactly 2 titles are all left out together, so alphabetical order never decides which topics appear.
- **Accessible by design.** The font is [Atkinson Hyperlegible](https://www.brailleinstitute.org/freefont/), which gives easily confused characters (I/l/1, b/d, O/0) distinct shapes. The colours are three shades of a single blue, so they read the same with any colour vision deficiency, and each has at least 4.7:1 contrast with its background.

Every choice can be reviewed and edited in plain CSV and JSON files. [wordclouds/README.md](wordclouds/README.md) documents the full method.

## Reproduce

Requires Python 3.12. From the repository root:

```sh
python3.12 -m venv .venv-wordcloud
.venv-wordcloud/bin/python -m pip install -r wordclouds/requirements.txt
.venv-wordcloud/bin/python wordclouds/fetch_corpus.py       # downloads the 263 records from Europe PMC
.venv-wordcloud/bin/python wordclouds/prepare_corpus.py     # checks them and builds data/ corpus
.venv-wordcloud/bin/python wordclouds/generate.py           # writes wordclouds/outputs/
.venv-wordcloud/bin/python wordclouds/test_processing.py    # 19 processing checks
```

Runs are deterministic: two runs with different Python hash seeds produce byte-identical images and tables ([reproducibility_check.json](wordclouds/reproducibility_check.json)). Package versions are pinned, and the font is bundled.

The abstracts are not stored in this repository (see [Data and licences](#data-and-licences)). `prepare_corpus.py` checks every downloaded title and abstract against a SHA-256 fingerprint of the 4 October 2026 snapshot used for the published images, so a successful build reproduces them exactly. If Europe PMC has since corrected a record, the script names it and stops; `--allow-changes` builds from the current records instead.

## Repository contents

| Path | Contents |
| --- | --- |
| [`simd_papers.csv`](simd_papers.csv) | The 263 papers: year, PMID, DOI, title, PDF status, Europe PMC link, and fingerprints of the title and abstract |
| [`simd_252_papers_year_pmid_abstract.csv`](simd_252_papers_year_pmid_abstract.csv) | The original paper list, kept unchanged. Its abstracts are title-based template sentences, so it is not used for counting |
| [`simd_pmids_not_downloaded.txt`](simd_pmids_not_downloaded.txt) | The 4 papers that still have no PDF (updated 14 October 2026). They are included in the corpus. The 11 papers flagged by `Added_from_missing_list` in simd_papers.csv were the missing-PDF list on 4 October |
| [`wordclouds/fetch_corpus.py`](wordclouds/fetch_corpus.py), [`prepare_corpus.py`](wordclouds/prepare_corpus.py) | Download the records by PMID and build the checked corpus |
| [`wordclouds/generate.py`](wordclouds/generate.py) | Counting and rendering |
| [`wordclouds/term_groups.csv`](wordclouds/term_groups.csv), [`exclusions.csv`](wordclouds/exclusions.csv), [`settings.json`](wordclouds/settings.json) | Editable rules: phrases and spelling variants, excluded wording, thresholds, cloud shape, font and colours |
| [`wordclouds/outputs/`](wordclouds/outputs/) | PNG (300 dpi) and SVG clouds, exact frequencies, per-paper terms and a run manifest with input and output hashes |

To switch back to single-word clouds or a rectangular layout, change `phrases.enabled` or `shape.fields` in `settings.json` and rerun.

## Data and licences

- **Paper metadata:** titles and abstracts come from the [Europe PMC](https://europepmc.org/) records for each PMID. Abstracts remain the copyright of their publishers and authors, so this repository does not include them: it shares bibliographic data (PMID, DOI, year, title) and one-way fingerprints, and `fetch_corpus.py` downloads the text from Europe PMC. The images and tables contain only phrases of at most three words.
- **Font:** Atkinson Hyperlegible © Braille Institute of America, under the [SIL Open Font License 1.1](wordclouds/assets/AtkinsonHyperlegible-OFL.txt).
- **Rendering:** uses the MIT-licensed [wordcloud](https://github.com/amueller/word_cloud) package.
- **Code:** [MIT licence](LICENSE).
- **Images, rules and frequency tables** (`wordclouds/outputs/`, `term_groups.csv`, `exclusions.csv`, `settings.json`): [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/). Please credit "SIMD literature word clouds, Michele Tinti".
