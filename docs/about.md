# About & Methodology

## What this is

A curated catalog of generative-AI / ML **tasks** relevant to **game and anime production**,
organized as an _Area → Task_ tree. For each task we track:

- **Open-source models & papers** — the bulk of the catalog (each anchored to an arXiv paper
  and/or a real code repository), and
- **Proprietary / industry tools** in active production use.

## How entries are discovered

A GitHub Actions job runs **weekly**. It invokes an agent equipped with read-only discovery tools:

- **arXiv** — recent papers per task
- **Hugging Face** — trending papers and model releases
- **GitHub** — new/active repositories
- **DuckDuckGo** — general web search

The agent rotates its focus across areas week to week to broaden coverage.

## Why you can trust the data

The agent only **proposes** entries. A deterministic pipeline then:

1. **Validates** every record against a strict schema and the taxonomy.
2. **Recomputes** the canonical id and de-duplication key (it never trusts the agent's).
3. **Verifies** that the primary link actually resolves, and requires open-source entries to be
   anchored to an arXiv id or a GitHub repository.
4. **De-duplicates** against everything already in the catalog.
5. **Merges** conservatively — filling only empty fields, **never** overwriting human edits.

The result is a Pull Request that a human reviews and merges. Thumbnails are auto-extracted
(arXiv figure → Open Graph image → placeholder).

!!! warning "Automated curation"
    Summaries are machine-generated and kept deliberately neutral. They may contain mistakes —
    treat this as a discovery aid, not an authoritative source. Corrections via PR are welcome.

## Editing the taxonomy

The Area → Task structure lives in a single file, `taxonomy.yml`. Adding, renaming, or removing
a task is a one-file edit; the navigation and all pages regenerate from it on the next build.

## License

Project code is [MIT](https://opensource.org/license/mit). Catalog entries are bibliographic
metadata about third-party works that remain under their own respective licenses.
