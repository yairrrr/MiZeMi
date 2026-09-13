# Building the offline group reference bundle

Production reads the committed, validated JSON under `backend/app/data/knowledge`. It never runs a fetch/build script. Neon stores application/game records only. See [KNOWLEDGE_BASE_REPORT.md](../../KNOWLEDGE_BASE_REPORT.md) for final counts, benchmarks, sample games and limitations.

## Sources and rights

- [Wikidata structured data](https://www.wikidata.org/wiki/Wikidata:Licensing): CC0. Reviewed seed records were retrieved on 2026-09-11; the bounded expansion over 2026-09-13–14. Fields: entity IDs, short English/Hebrew labels and sitelink titles, P136 genre, P31 instance, P279 subclass, P2012 cuisine, P495 origin, P577 release, P179 series and P175 performer. No article text, descriptions, biographies, plots, lyrics, posters or raw API responses are redistributed.
- [GeoNames IL extract](https://download.geonames.org/export/dump/IL.zip), [format and license](https://download.geonames.org/export/dump/readme.txt): CC BY 4.0, refreshed 2026-09-13. The compressed input was 582,338 bytes. **Contains information from GeoNames, available under CC BY 4.0. MiZeMi filtered, normalized and adapted the data.** The source/license notice and accessible application credits must accompany redistribution. GeoNames is an aggregation, not an official Israeli administrative register; names and coverage make no sovereignty assertion.
- The [official Population Authority locality dataset](https://data.gov.il/he/datasets/population_authority/citiesandsettelments) and CBS listings were investigated. The keyless CKAN package metadata advertised `other-open` without a specific license URL; no bulk government CSV was imported under unclear terms.
- [MusicBrainz](https://musicbrainz.org/doc/About/Data_License) has different core and supplementary/tag licenses. No MusicBrainz tags, IMDb/TMDB bulk metadata, paid/keyed sources or copyrighted prose were imported.
- `group-curation.json.review_notes` records factual spot checks and conservative inclusion overrides. The Eden Ben Zaken record retains only corroborated Mizrahi/pop classifications; questionable unreferenced classical/folk/soul seed claims are excluded. The Apple Music curator page is a spot-check source only; no Apple catalog, text or API data is imported. Authored factual inclusion policies and aliases are dedicated to CC0 alongside the Wikidata projections.

## Coverage selection and transformations

`scripts/expand_knowledge.py` is development-only and requires an explicit `--fetch`. It selects finite popularity-ranked film, song, artist, dish and activity pools. Sitelink counts only select useful reference coverage; they NEVER determine a game answer or predict a participant's taste. A second pass adds Hebrew-linked works, a focused Israeli-artist selection, animated films, reviewed seeds and popular video games as digital hobbies. Candidates without supported useful classifications are omitted. The query text and finite limits are in the script; compact cache selections retain their queries and dates.

The source sometimes returns 429 or times out. The build stops on 429/Retry-After, resumes from completed batches only after the requested interval, and uses bounded transient retries. Fixed-root activity queries replace an expensive variable-root graph traversal. Requests are sequential and paced. Do not bypass provider limits. See [WDQS graph split](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/WDQS_graph_split) and [API etiquette](https://www.mediawiki.org/wiki/API:Etiquette).

The offline compiler merges these factual projections with `curation.json` (reviewed v1 seeds/roots) and `group-curation.json` (activity roots, setting policies, regions, aliases and review overrides). Genre closure follows at most two P279 edges. Food/activity closure follows at most three, plus immediate P31 and bounded cuisine ancestry. Musical instruments mean playing that instrument in the hobby context. Songs use their OWN P136 statements, never a performer's typical genres. Unknown-value blank nodes are discarded. Explicit disambiguation/list/person-as-hobby and adult-film types are excluded.

Food cuisine/region associations are not exclusive national-origin claims. Formats overlap. No allergy, vegetarian or vegan guarantee is inferred. Physical sports differ from tabletop/mind games. Fitness contributes to the broad sport family; playing instruments contributes to creative hobbies. Broad-family answer choices exclude their own narrower child families. Setting classifications describe the conventional activity setting, not where a person actually practises it. Flexible activities belong to neither indoor nor outdoor totals; unsupported settings stay unknown.

Regions group provider districts: Northern + Haifa → north; Central + Tel Aviv → center; Southern → south; Jerusalem stays separate. Unsupported district codes remain unknown. Geographic comparisons can still use known coordinates. Keep PPL/PPLA/PPLA2/PPLA3/PPLC; exclude historic/abandoned places and neighborhood PPLX. Coordinates are rounded to five decimals, and pairwise distances are calculated, never stored.

Names are conservative: canonical English/Hebrew sitelink names when available, fallback labels otherwise, reviewed spellings, short film/song disambiguation aliases and year/performer-qualified names. Activity qualifiers are retained unless a synonym is reviewed: a narrower track-running discipline must not mask general running. No bulk upstream alias harvesting or fuzzy matching. The earlier research encountered vandalized aliases, so simply importing every alias is intentionally avoided. Remakes and same-name songs collide and stay UNKNOWN unless qualified. A normalized canonical label has no priority over a colliding alias. Unknown input remains available to consented direct fallback rules.

Reviewed taxonomy edges can also be excluded: disaster-film membership alone is not accepted as evidence of the thriller genre. The exclusion does not remove independently supported thriller statements. These decisions are recorded with source links in `group-curation.json.review_notes`.

## Rebuild and review

```sh
# Offline validation only (safe for CI; never downloads anything).
.venv/bin/python scripts/build_knowledge_base.py

# Development only. Use a NEW cache for a source refresh; reuse it to resume.
.venv/bin/python scripts/expand_knowledge.py --fetch /tmp/mizemi-reference-review
.venv/bin/python scripts/expand_knowledge.py --fetch /tmp/mizemi-reference-review --hebrew
.venv/bin/python scripts/expand_knowledge.py --fetch /tmp/mizemi-reference-review --places-only

# Review compact facts, source dates and curation. Compile offline to a draft.
.venv/bin/python scripts/compile_group_knowledge.py /tmp/mizemi-reference-review \
  --output /tmp/mizemi-reference-draft --version YYYY-MM-DD.1 --retrieved YYYY-MM-DD
.venv/bin/python scripts/audit_group_questions.py --bundle /tmp/mizemi-reference-draft \
  --output /tmp/mizemi-game-review.json

# After source/alias/fact/style review, compile to the real asset directory
# with the same reviewed cache/date/version by omitting --output.
.venv/bin/python scripts/benchmark_knowledge.py
.venv/bin/python scripts/audit_group_questions.py
```

`build_knowledge_base.py --refresh/--compile` remains the historical small-seed builder. Use the new expansion/compiler for schema 2. Source caches stay outside the repository and are not runtime dependencies. Public refreshes can change facts and are not byte-identical; bump the bundle version. The same cache, base seeds, curation, date and compiler produce identical artifacts, verified by tests. `compile_group_knowledge.py --base` can pin the seed bundle during review.

Runtime rows contain canonical ID, English/Hebrew names, bounded aliases, shared category IDs, optional coordinate pair, retained seed revision and optional compact details. New records use revision 0 because WDQS does not return entity revisions: provenance is the dated query projection, selection/curation hashes and artifact hashes, not an invented revision. Seed facts may be augmented by the dated expansion. `manifest.json` records these transformations. Checksums detect accidental corruption, not upstream factual errors. Long-tail community classifications require continued review.

All JSON is schema/type/size/hash validated before indexing. Files with duplicate IDs/keys/options, invalid domains, bad metadata, nonfinite/out-of-region coordinates, unsupported licenses, symlinks or unexpected paths fail closed. Runtime indexes and immutable classification sets are built once; compact JSON stays comfortably below the asset budget without a compression dependency. Compression is measured for repository impact, not required at startup.
