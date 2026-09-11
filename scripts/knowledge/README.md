# Building MiZeMi’s offline reference bundle

Production reads the committed JSON in `backend/app/data/knowledge`. It never runs these scripts or accesses a reference provider. The catalog has **2,434 entities**: 467 films, 282 artists, 66 music styles, 182 foods, 212 hobbies and 1,225 localities. It deliberately omits entries without supported classifications.

## Sources and licensing

All sources were investigated/retrieved on **2026-09-11**.

- [Wikidata structured data](https://www.wikidata.org/wiki/Wikidata:Licensing) is CC0. We use entity IDs, revisions, English/Hebrew sitelink titles, P136 (genre), P279 (subclass), P31 (instance) and P2012 (cuisine), plus a small, explicitly listed set of reviewed classifications from factual entity descriptions. Descriptions themselves are **not** retained. A record’s Q ID and revision reconstruct its source URL: `https://www.wikidata.org/w/index.php?title=Q…&oldid=…`.
- [GeoNames country extract](https://download.geonames.org/export/dump/IL.zip), [format/licensing](https://download.geonames.org/export/dump/readme.txt), and [district code table](https://download.geonames.org/export/dump/admin1CodesASCII.txt): CC BY 4.0. Only populated-place features and six district codes are used. The original compressed country extract was 581,687 bytes. Attribution is shipped in the manifest, dataset license notice, this document and the application’s accessible credits. **Contains information from GeoNames, available under CC BY 4.0. MiZeMi filtered, normalized and adapted the data.**
- Israeli [CBS open-data listings](https://data.gov.il/he/organizations/lamas) were investigated as an official alternative. Retrieval/redistribution terms could not be verified reliably for the locality spreadsheets, so no CBS bulk data was imported. GeoNames has explicit reusable terms and publishes its sources; it is an aggregation, not an authoritative Israeli administrative register.
- [MusicBrainz licensing](https://musicbrainz.org/doc/About/Data_License) was reviewed. Its core metadata and supplementary/tag licenses differ; no MusicBrainz genre-tag data was imported. No IMDb/TMDB descriptions, posters, cast lists, copyrighted prose, paid/keyed sources or Wikipedia article text was copied.
- The [BBFC classification for The Conjuring](https://www.bbfc.co.uk/release/the-conjuring-q29sbgvjdglvbjpwwc0znzgwmjc) independently corroborates the horror classification; no BBFC prose was copied. Saw uses Wikidata **Q486239**, the feature film, rather than its short film or franchise entities. Its retained classifications include horror and crime; this bundle does **not** invent a thriller membership for Saw from the task’s example.

## Selection and transformation

`curation.json` is the development recipe: selected entity IDs, bilingual taxonomy labels, approved classification roots, individually reviewed hobby families, explicit food additions, known aliases and modern place-name overrides. It contains no biography, plot, image URL, population or raw response.

Initial discovery investigated 502 film titles, 316 artist names, 239 foods, 237 activities and 101 genre/concept titles using the MediaWiki entity API. Some titles were redirects/disambiguations/missing; the resolved pools contained 473 films, 295 artists, 224 foods and 217 activities. Entries lacking the required positive classifications were omitted. Adding uncertain long-tail records was less useful than improving Hebrew coverage and aliases. The music table additionally includes hip-hop, Mediterranean music and the local lexical subtype “Israeli pop”.

Genre enrichment follows P136 to approved genre roots with at most two P279 edges. Food enrichment uses at most three P279 edges, immediate P31 and P2012. It never equates origin, ethnicity, influence or ingredient association with genre/cuisine membership. Cuisines describe associations, not exclusive national ownership. Broad regional cuisine groupings are authored taxonomy choices; there are no dietary/allergy promises.

Hobby families are an explicit reviewed activity taxonomy, rather than an unrestricted walk through Wikidata’s ontology. Instruments in the hobby context mean making music. Physical sports are separated from tabletop/mind games; travel is not a claim about sociability. A selected Israeli-pop style is classified as pop by definition; it never infers an artist’s nationality or a listener’s playlist.

Wikidata labels/aliases are not blindly trusted. The discovery encountered vandalized English aliases for Saw and a bad Hebrew label for Jachnun. Canonical enwiki/hewiki sitelink titles replace raw labels where available, and broad alias harvesting is disabled. Short disambiguated titles become aliases; collisions are rejected even against another canonical name. Remakes sharing a name require a distinguishing title/year when ambiguous in this catalog. Manual spellings are conservative, not fuzzy matching.

GeoNames filtering keeps PPL/PPLA/PPLA2/PPLA3/PPLC; excludes historic/abandoned feature classes and neighborhood PPLX. One modern Hebrew name is selected, preferring the pointed form when present, with reviewed overrides and explicit common aliases. Bulk alternate names are dropped: they can contain ancient names and unrelated settlements. English primary/ASCII names are retained. Duplicate place names remain UNKNOWN unless a distinct supported name is supplied. Names/coverage follow the provider and make no sovereignty assertion. Unknown district codes remain absent (22 records), while usable coordinates can still support geographic rules. No pairwise distances are stored.

## Rebuild/update commands

```sh
# Default is strictly offline: validate the shipped hashes and schema.
.venv/bin/python scripts/build_knowledge_base.py

# DEVELOPMENT ONLY, explicit public network access, no credentials:
# Use a NEW empty directory for an update; an existing cache resumes a fetch.
.venv/bin/python scripts/build_knowledge_base.py --refresh /tmp/mizemi-reference-review

# Review the compact cache and curation first, then compile into a draft folder.
.venv/bin/python scripts/build_knowledge_base.py \
  --compile /tmp/mizemi-reference-review \
  --output /tmp/mizemi-reference-draft \
  --version YYYY-MM-DD.1 --retrieved YYYY-MM-DD

# Validate the draft, review its diff/provenance, then compile to the real
# asset directory with the same reviewed cache/version/date (omit --output).
# Run the full regression suite and regenerate measurements/demonstrations:
.venv/bin/python scripts/benchmark_knowledge.py
```

Refresh uses one API request at a time, batches of at most 40 entities, 1.1-second pacing, bounded ancestor expansion, timeouts and bounded retries for transient responses. Respect a longer Retry-After by stopping and resuming later; do not work around restrictions. During initial research WDQS reported an outage/429; it was abandoned instead of repeatedly queried. The ordinary MediaWiki entity API was used. Deployment never depends on SPARQL or fetching a dump.

The committed version was compiled from the reviewed discovery cache with `--version 2026-09-11.1 --retrieved 2026-09-11`. Source revisions and artifact hashes preserve provenance. A later public-source refresh is **not guaranteed byte-identical**: providers change. Review changed facts and bump the dataset version. The same reviewed cache, curation, builder, version and retrieval date produce identical artifacts, which is tested. Raw caches stay outside the repository. JSON is one compact entity array per line; memory indexes are rebuilt once per process.

The manifest is a checksum/schema integrity check, not a cryptographic assertion that every upstream fact is true. All future source/curation changes require review. Runtime rejects malformed, oversized, duplicate, mismatched, symlinked or incorrectly typed artifacts before they can be used for scoring.
