# publishing-skills

Four composable skills that turn an AI coding agent (Claude, Cursor, Codex, Gemini, Copilot, ...) into a long-tail SEO publishing pipeline. **Platform-agnostic** - works against Ghost, WordPress, Webflow, Sanity, Strapi, or any static-site generator (Hugo, Astro, Eleventy, Jekyll, Next-MDX).

Built for indie hackers, founders, content marketers, and dev-tool teams that want a repeatable, source-grounded publishing workflow - not paraphrased docs, hallucinated benchmarks, or generic "ultimate guide" filler. Search rankings and AI citations are outcomes to measure, not guarantees these skills make.

| Skill | What it does | Who it's for |
|---|---|---|
| **`blog-topic-research`** | Builds a deduplicated backlog from current public demand signals and authoritative sources. Every accepted topic carries traceable evidence, intent, version context, and an explicit duplicate decision; scores are editorial signals, never invented search volume. | Editorial teams that need to decide what is worth writing before drafting begins. |
| **`seo-blog-writer`** | Researches, drafts, validates, and hands off one long-tail article. It produces a local review bundle by default, adds structured data only when visible content qualifies, and invokes Ghost, WordPress, static-site, or documented custom adapters only after explicit approval. | Teams that need source-to-claim coverage and a controlled CMS handoff. |
| **`blog-figure-svg`** | Designs accessible, source-backed SVG flows, comparisons, taxonomies, terminal mocks, and feature cards. It blocks unsupported claims and active SVG content; optional PNG rasterization stays local until upload is approved. | Publishers that need editorial figures with accessibility and evidence receipts. |
| **`blog-editorial-calendar`** | Maintains an evidence-backed backlog, deterministically selects the next eligible item against configured cluster and format targets, reserves publishing slots, and reconciles local state with the real CMS before mutation. | Teams that need an auditable cadence without silently changing live publishing state. |

Together, they form a controlled pipeline: **plan the cadence → research the topic → draft the post → illustrate it → review → publish through an approved adapter**.

## Installing

### Via skills.sh (any agent runtime)

Installs all 4 skills into Claude Code, Cursor, Codex, Gemini CLI, GitHub Copilot, and 50+ other runtimes at once:

```bash
npx skills add AutomateLab-tech/publishing-skills
```

### Via clawhub CLI (Claude / OpenClaw runtimes)

```bash
npm i -g clawhub
clawhub login
clawhub skill install blog-topic-research
clawhub skill install seo-blog-writer
clawhub skill install blog-figure-svg
clawhub skill install blog-editorial-calendar
```

### Manually

Each skill is a single `SKILL.md` file with YAML frontmatter. Drop it into your project's `.claude/skills/<name>/` directory (or your agent runtime's equivalent skill folder) and reload.

```bash
git clone https://github.com/AutomateLab-tech/publishing-skills.git
cp -r publishing-skills/skills/* .claude/skills/
```

## How they compose

```
+----------------------+      +--------------------------+      +-------------------+      +-------------------+
| blog-topic-research  | ---> | blog-editorial-calendar  | ---> |  seo-blog-writer  | <--- |  blog-figure-svg  |
| 'is the topic worth  |      | 'pick the next topic to  |      | 'write + publish' |      | 'illustrate the   |
|  writing about?'     | <--- |  balance the corpus +    |      |                   |      |   post'           |
+----------------------+ refill  schedule the cadence'   |      +-------------------+      +-------------------+
                              +--------------------------+               |
                                                                         v
                                              +----------------------------------+
                                              | platform adapter (one of):       |
                                              |   - Ghost Admin API              |
                                              |   - WordPress REST API           |
                                              |   - static-site file output      |
                                              |   - bring-your-own (~20 lines)   |
                                              +----------------------------------+
```

- **`blog-topic-research`** runs first and separates observed demand from editorial judgment before drafting.
- **`blog-editorial-calendar`** selects and reserves work against the approved target mix, but requires owner approval before scheduling, publication, or backlog mutation.
- **`seo-blog-writer`** consumes the evidence scaffold (or builds one), produces a local bundle, validates it, and uses a platform adapter only for the explicitly approved target state.
- **`blog-figure-svg`** runs standalone or from the illustration phase when a post needs a sourced chart, diagram, terminal mock, or feature card.

## Safety model

- Local drafts and dry runs are the default. Live publication, scheduling, overwrite, deletion, asset upload, and CMS reconciliation changes require content-owner approval.
- Credentials stay in environment variables or an approved secret store. Skills must not place secrets in prompts, URLs, drafts, fixtures, logs, or receipts.
- Volatile product, performance, pricing, legal, medical, financial, and security claims require current authoritative sources and the appropriate human review.
- Every live mutation is re-read from the target system and recorded with its resulting state, identifier, canonical URL, and a secretless receipt.

## Requirements

- **`blog-topic-research`** - no system dependencies beyond `WebSearch` / `WebFetch` in the agent runtime.
- **`seo-blog-writer`** - Python 3 for the optional local validators and bundled adapters. Platform-specific extras:
  - **Ghost adapter**: `pip install requests pyjwt`; `GHOST_URL` + `GHOST_ADMIN_KEY` env vars.
  - **WordPress adapter**: `pip install requests`; `WP_URL` + `WP_USER` + `WP_APP_PASSWORD` env vars.
  - **Static-site adapter**: no credentials; just a target directory in your SSG repo.
- **`blog-figure-svg`** - Python 3, plus one SVG rasterizer (ImageMagick / `rsvg-convert` / Inkscape / `cairosvg`) and optionally `pngquant` for compression.

### Optional - ai-seo MCP (programmatic citation scoring)

`seo-blog-writer` Step 5 (AI-SEO audit) runs a programmatic citation-worthiness and schema pass when the [**ai-seo MCP**](https://github.com/AutomateLab-tech/ai-seo-mcp) (`@automatelab/ai-seo-mcp`) is connected. The skill checks at preflight and prompts you to install it if it's missing. Without it, Step 5 falls back to a manual reasoning pass covering the same ground.

```bash
npx -y @automatelab/ai-seo-mcp
```

Then register it in your agent's MCP config. See the [ai-seo-mcp README](https://github.com/AutomateLab-tech/ai-seo-mcp) for one-line configs for Claude Code, Cursor, and Cline.

## Maintenance scripts

The per-post audit inside `seo-blog-writer` catches structural problems before publish. For corpus-wide drift - characters or banlist phrases that crept back across many posts - run [`scripts/audit-corpus.py`](scripts/audit-corpus.py) against your content directory:

```bash
python3 scripts/audit-corpus.py path/to/your/content/
python3 scripts/audit-corpus.py content/posts/ --extra "synergy,best-in-class"
```

Exits `0` clean / `1` on hits - composes with CI for a pre-deploy drift gate.

## Glossary auto-link

`seo-blog-writer` Step 7i (optional) pipes the draft HTML through [`scripts/inject-glossary-links.py`](scripts/inject-glossary-links.py), which wraps the first mention of each known technical term in an internal link to its definition page and writes a `data-definition` attribute for hover tooltips. Schema and starter file in [`skills/seo-blog-writer/references/glossary-schema.md`](skills/seo-blog-writer/references/glossary-schema.md); a self-contained tooltip-rendering snippet for your site `<head>` is at [`skills/seo-blog-writer/references/decorate.js`](skills/seo-blog-writer/references/decorate.js).

```bash
python3 scripts/inject-glossary-links.py post.html \
    --glossary glossary.json --base-url /glossary/ > post.linked.html
```

The injector handles the awkward edges automatically: first-occurrence-only per post, longest-alias wins, skips headings / code / tables / blockquotes / TL;DR, and rejects matches embedded in identifier-like compounds (`user-agent` won't match `agent`, `@scope/ai-seo-mcp` won't match `mcp`). You bring the glossary file and the definition pages; the injector handles the linking.

## Why platform-agnostic?

The writing pipeline (research, classify, draft, scrub, AI-SEO audit, JSON-LD generation) is the hard part. The publish step is glue. Coupling the two means you're locked into one CMS forever - and if you move from Ghost to WordPress, you rewrite the whole skill.

This repo separates them. The writer produces a stable bundle (`<slug>.draft.html`, `<slug>.schema.html`, `<slug>.metadata.json`) and the adapter ships it. Add Webflow, Sanity, or Strapi in an afternoon without touching the pipeline.

## License

[MIT-0](LICENSE) - public domain equivalent. Use, modify, redistribute without attribution.
