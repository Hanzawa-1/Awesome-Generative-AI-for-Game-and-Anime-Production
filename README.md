# Awesome Generative AI for Game & Anime Production

A curated, **self-updating** catalog of generative-AI / ML **tasks** for **game and anime
production** — published as a bilingual (EN / 日本語) website. Each task collects the open-source
models & papers and the proprietary tools studios actually use, with previews at a glance.

> **Live site:** _set after first deploy_ → `https://<user>.github.io/<repo>/`

## What's inside

The catalog is organized as an **Area → Task** tree across 8 areas:

- **Image & 2D Art** — text-to-image, ControlNet, line-art colorization, anime upscaling, …
- **3D Generation** — text/image-to-3D, mesh & CAD generation, texture/PBR, scenes, 3D editing
- **Characters & Avatars** — character/face generation, auto-rigging, skinning
- **Animation & Motion** — motion capture, retargeting, frame interpolation / inbetweening
- **Video** — text/image-to-video, restoration, rotoscoping
- **Audio** — TTS, voice cloning, singing-voice synthesis, music & SFX
- **Text, Narrative & Design** — NPC dialogue, quests, procedural content, localization
- **Manga & Comics** — panel/page generation, layout, colorization

Each entry is a card with a preview, a neutral EN + JP summary, tags, and source links
(arXiv / GitHub / project / Hugging Face / website). Cards added by the agent carry a
**“Discovered by AI”** badge; human-curated entries carry none.

## How it stays fresh

A weekly GitHub Actions job runs an agent (arXiv · Hugging Face · GitHub · web) that discovers new
work, validates and de-duplicates it, and opens a **Pull Request** for human review. Nothing reaches
the site without passing schema + link checks and a human merge.

- **Source of truth:** `data/entries.yml` (open source) and `data/services.yml` (proprietary) — the
  site is generated from these.
- **Taxonomy:** `taxonomy.yml` defines the Area → Task tree (a one-file edit to grow it).
- See **[How it works](docs/about.md)** for the full methodology, and
  **[Get started](docs/get-started.md)** to run it locally, run the agent, and deploy.

## Contributing

Add or correct an entry by editing `data/entries.yml` / `data/services.yml` (schema in
`agent/schema.py`) and opening a PR — the agent's merge never overwrites human-edited fields.
See [Get started](docs/get-started.md#contributing).

## License

Code: [MIT](LICENSE). Catalog entries are bibliographic metadata about third-party works, each of
which remains under its own license.
