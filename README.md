# repotalk

AI-powered codebase documentation generator. Crawls a Python codebase, builds a knowledge graph via AST analysis, and uses configurable LLMs to generate hierarchical documentation with a RAG chat interface.

## How It Works

```
Source Code → AST Analysis → Knowledge Graph → LLM Docs → Rollup Summaries → Chat/RAG
              (free)          (free)           (per-file)   (per-directory)    (interactive)
```

**Phase 1 — Analyze** (free, no LLM): Crawls files, parses AST, extracts imports/functions/classes/calls, builds a NetworkX knowledge graph with typed edges (imports, calls, inherits, composes, decorates).

**Phase 2 — Document** (LLM): Generates per-file `.md` documentation in a mirror tree. Each doc has: Purpose, Dependencies, Classes, Functions, Data Flow, Side Effects.

**Phase 3 — Enrich** (LLM): Annotates knowledge graph edges with human-readable descriptions of how modules interact.

**Phase 4 — Rollup** (LLM): Bottom-up hierarchical summaries — leaf directories first, then parent directories, then a top-level project overview.

**Chat** (LLM): Interactive REPL that retrieves relevant docs via keyword or vector search and answers questions about your codebase.

## Installation

```bash
pip install -e .

# With vector search support (ChromaDB):
pip install -e ".[vector]"
```

## Quick Start

```bash
# 1. Copy and edit config
cp config.example.yaml repotalk.yaml
# Edit repotalk.yaml — add your API keys

# 2. Run all phases
repotalk run ./my-project

# Or run phases individually:
repotalk analyze ./my-project    # Free — AST + graph
repotalk document ./my-project   # LLM — per-file docs
repotalk enrich ./my-project     # LLM — graph annotations
repotalk rollup ./my-project     # LLM — hierarchical summaries

# 3. Chat with your codebase
repotalk chat ./my-project

# 4. Export context for external LLM use
repotalk context ./my-project "how does authentication work"

# 5. Check stats and cost estimates
repotalk stats ./my-project
```

## Configuration

Config is loaded from `repotalk.yaml` (searched upward from target path). See `config.example.yaml` for all options.

### Model Selection

Uses [litellm](https://docs.litellm.ai/) so any provider works:

| Phase | Default Model | Notes |
|-------|--------------|-------|
| File docs | `gemini/gemini-2.5-flash` | High volume — use fast/cheap |
| Graph enrichment | `gemini/gemini-2.5-flash` | High volume — use fast/cheap |
| Rollup summaries | `gemini/gemini-2.5-pro` | Lower volume — use smarter |
| Chat | `anthropic/claude-sonnet-4-20250514` | Quality matters most |
| Embeddings | `openai/text-embedding-3-small` | Only for vector retrieval |

### API Keys

Set in config or via environment variables:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`

## Output Structure

```
docs-mirror/
├── PROJECT_OVERVIEW.md          # Top-level summary
├── knowledge_graph.json         # Full graph data
├── knowledge_graph.mmd          # Mermaid diagram
├── module_a/
│   ├── _summary.md              # Directory rollup
│   ├── __init__.py.md           # Per-file doc
│   ├── core.py.md
│   └── utils.py.md
└── module_b/
    ├── _summary.md
    └── ...
```

## Features

- **Incremental updates**: Tracks file hashes — only re-documents changed files
- **Concurrency**: Parallel LLM calls with configurable semaphore
- **Cost tracking**: Logs tokens used and estimated cost per phase
- **Progress bars**: Rich console output with spinners and progress
- **Any LLM provider**: OpenAI, Anthropic, Google, DeepSeek, local via Ollama
- **Knowledge graph**: Queryable NetworkX graph with Mermaid export
- **RAG chat**: Keyword or vector (ChromaDB) retrieval
- **Context export**: Pull relevant docs for pasting into external LLMs

## Cost Estimates

For a ~5,000 line Python project (~50 files):

| Phase | Gemini Flash | GPT-4o-mini | Claude Sonnet |
|-------|-------------|-------------|---------------|
| File docs | ~$0.01 | ~$0.03 | ~$0.30 |
| Graph enrichment | ~$0.005 | ~$0.01 | ~$0.15 |
| Rollup | ~$0.01 | ~$0.02 | ~$0.20 |
| **Total** | **~$0.03** | **~$0.06** | **~$0.65** |

Gemini Flash is recommended for bulk documentation phases. Use a stronger model for chat.

## Architecture

```
cli.py ──→ crawler.py ──→ analyzer.py ──→ graph.py
                │                            │
                ▼                            ▼
          documenter.py ◄─── llm_client.py ──→ rollup.py
                │                                  │
                ▼                                  ▼
           output.py ◄────────────────────────────┘
                │
                ▼
          chat.py ◄── retriever.py ◄── embedder.py
```

- **models.py**: Pydantic data models shared across all modules
- **config.py**: YAML config loading with Pydantic validation
- **llm_client.py**: Unified async LLM interface via litellm with retry and cost tracking

## License

MIT
