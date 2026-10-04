# Refined phrase pairings

The revised clouds use explicit phrases and a small number of documented concept families. They do not merge every socioeconomic label into one umbrella. The 263-paper input corpus, font, palette and fixed seed are unchanged.

## Decisions

| Text observed | Canonical term or action | Reason |
| --- | --- | --- |
| deprivation; socioeconomic/social/area deprivation; deprived; deprivation status | deprivation | One deprivation topic family; original forms remain auditable. Different measurement levels and deprivation degrees are not equated. |
| socioeconomic status; socioeconomic position; SES; SEP | socioeconomic status | An explicit status/position family, separate from deprivation. |
| socioeconomic inequalities; health inequalities | socioeconomic inequality; health inequality | Preserve the qualifier; retain generic inequality separately. |
| health status; smoking status; vaccine status; performance status | health status; smoking status; vaccination status; performance status | Pair status with its explicit qualifier. These are not socioeconomic status. |
| socioeconomic factors/circumstances/gradients/differences | Corresponding complete phrase | Retain the noun rather than guessing the construct. |
| standalone socioeconomic; standalone status | Exclude | Incomplete or ambiguous phrase. |

The earlier suggestion to collapse everything into “Socioeconomic conditions” remains available as a disabled proposal. The current version retains more meaning. Phrase matching now stops at sentence/section punctuation. Longest phrases win, so “socioeconomic deprivation status” is counted as deprivation and does not leave a stray “status”.

## Counts after refinement

A family contributes at most once per paper. Counts are recomputed from the corpus; frequencies of aliases are not simply added. Each column has 263 papers. Protected phrases can be absent from the cloud when they fall below the frequency threshold or displayed-term limit; they remain in the full tables.

| Canonical term | Titles mentioning it | Abstracts mentioning it |
| --- | ---: | ---: |
| deprivation | 87 | 203 |
| socioeconomic status | 19 | 59 |
| socioeconomic inequality | 13 | 19 |
| health inequality | 2 | 21 |
| inequality | 15 | 48 |
| health status | 1 | 5 |
| smoking status | 1 | 6 |
| vaccination status | 0 | 6 |
| performance status | 0 | 3 |
| socioeconomic factor | 1 | 12 |
| socioeconomic circumstance | 2 | 4 |
| socioeconomic gradient | 0 | 11 |
| socioeconomic difference | 3 | 2 |

[Review the contributing PMIDs and observed phrases](pairing_review.csv). [Browse all rules](outputs/review_terms.html). [View updated clouds](outputs/index.html).

Previous rules and images are preserved in `versions/before_pairing_refinement/`. The same original abstracts and titles are used; only counting/phrase rules and their explanation changed.
