"""Click CLI — commands: analyze, document, enrich, rollup, chat, context, run, stats."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from repotalk.config import Config, load_config

console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )
    # Quiet noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)


def _load_cfg(config: str | None, path: Path) -> Config:
    config_path = Path(config) if config else None
    return load_config(config_path=config_path, target_path=path)


@click.group()
@click.version_option(package_name="repotalk")
def cli() -> None:
    """repotalk — AI-powered codebase documentation generator."""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-c", "--config", "config_file", type=click.Path(), default=None, help="Config file path")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def analyze(path: Path, config_file: str | None, verbose: bool) -> None:
    """Phase 1: AST analysis + knowledge graph (free, no LLM calls)."""
    _setup_logging(verbose)
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.analyzer import analyze_file
    from repotalk.crawler import crawl
    from repotalk.graph import KnowledgeGraph
    from repotalk.output import get_output_dir, write_analysis_cache, write_graph

    console.print(f"[bold]Analyzing[/bold] {root}")
    start = time.monotonic()

    files = crawl(root, cfg)
    console.print(f"Found [cyan]{len(files)}[/cyan] files")

    analyses = []
    for f in files:
        analysis = analyze_file(f, root)
        analyses.append(analysis)
        if analysis.errors:
            for err in analysis.errors:
                console.print(f"  [yellow]⚠ {analysis.relative_path}: {err}[/yellow]")

    # Build knowledge graph
    graph = KnowledgeGraph()
    graph.build_from_analyses(analyses)

    # Write outputs
    write_analysis_cache(analyses, root, cfg)
    write_graph(graph, root, cfg)

    elapsed = time.monotonic() - start
    stats = graph.stats()

    table = Table(title="Analysis Complete")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files analyzed", str(len(analyses)))
    table.add_row("Graph nodes", str(stats["total_nodes"]))
    table.add_row("Graph edges", str(stats["total_edges"]))
    table.add_row("Time", f"{elapsed:.1f}s")
    table.add_row("Output", str(get_output_dir(root, cfg)))
    console.print(table)


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-c", "--config", "config_file", type=click.Path(), default=None)
@click.option("-v", "--verbose", is_flag=True)
def document(path: Path, config_file: str | None, verbose: bool) -> None:
    """Phase 2: Generate per-file documentation via LLM."""
    _setup_logging(verbose)
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.documenter import document_all
    from repotalk.graph import KnowledgeGraph
    from repotalk.llm_client import LLMClient
    from repotalk.output import (
        get_output_dir,
        load_analysis_cache,
        load_hash_cache,
        save_hash_cache,
        write_file_docs,
    )

    analyses = load_analysis_cache(root, cfg)
    if not analyses:
        console.print("[red]No analysis cache found. Run 'analyze' first.[/red]")
        sys.exit(1)

    # Try to load graph
    graph = None
    try:
        graph = KnowledgeGraph.load(get_output_dir(root, cfg))
    except FileNotFoundError:
        pass

    hash_cache = load_hash_cache(root, cfg)
    client = LLMClient(cfg)

    console.print(f"[bold]Documenting[/bold] {len(analyses)} files with [cyan]{cfg.models.file_documentation}[/cyan]")

    docs = asyncio.run(document_all(analyses, root, client, cfg, graph, hash_cache))

    write_file_docs(docs, root, cfg)
    save_hash_cache(hash_cache, root, cfg)

    _print_cost_summary(client, "Documentation")


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-c", "--config", "config_file", type=click.Path(), default=None)
@click.option("-v", "--verbose", is_flag=True)
def enrich(path: Path, config_file: str | None, verbose: bool) -> None:
    """Phase 3: Enrich knowledge graph with LLM-annotated relationships."""
    _setup_logging(verbose)
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.graph import KnowledgeGraph
    from repotalk.llm_client import LLMClient
    from repotalk.output import get_output_dir, write_graph

    output_dir = get_output_dir(root, cfg)

    try:
        graph = KnowledgeGraph.load(output_dir)
    except FileNotFoundError:
        console.print("[red]No graph found. Run 'analyze' first.[/red]")
        sys.exit(1)

    client = LLMClient(cfg)
    console.print(f"[bold]Enriching graph[/bold] with [cyan]{cfg.models.graph_enrichment}[/cyan]")

    asyncio.run(_enrich_graph(graph, client, cfg))

    write_graph(graph, root, cfg)
    _print_cost_summary(client, "Graph Enrichment")


async def _enrich_graph(
    graph: KnowledgeGraph,
    client: LLMClient,
    config: Config,
) -> None:
    """Use LLM to annotate graph edges with descriptions."""
    from repotalk.models import EdgeType

    prompt_path = Path(__file__).parent.parent / "prompts" / "graph_enrich.md"
    system_prompt = prompt_path.read_text() if prompt_path.exists() else (
        "You are a code analyst. Given two code entities and their relationship, "
        "provide a brief (1-2 sentence) description of how they interact. "
        "Output only the description, nothing else."
    )

    file_nodes = graph.get_all_files()
    import_edges = [
        (s, t, d)
        for s, t, d in graph.graph.edges(data=True)
        if d.get("edge_type") == EdgeType.IMPORTS.value
        and s in file_nodes
        and t in file_nodes
    ]

    if not import_edges:
        console.print("[dim]No import edges to enrich.[/dim]")
        return

    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("Enriching edges...", total=len(import_edges))

        async def _enrich_edge(source: str, target: str, data: dict) -> None:
            context = (
                f"Source file: {source}\n"
                f"Target file: {target}\n"
                f"Relationship: imports\n"
                f"Imported names: {data.get('names', [])}"
            )
            try:
                description = await client.complete(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": context},
                    ],
                    model=config.models.graph_enrichment,
                    phase="graph_enrichment",
                    file_path=f"{source}->{target}",
                    max_tokens=256,
                )
                graph.graph.edges[source, target]["description"] = description.strip()
            except Exception as e:
                logging.getLogger(__name__).error("Error enriching %s->%s: %s", source, target, e)
            finally:
                progress.advance(task)

        tasks = [_enrich_edge(s, t, d) for s, t, d in import_edges]
        await asyncio.gather(*tasks)


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-c", "--config", "config_file", type=click.Path(), default=None)
@click.option("-v", "--verbose", is_flag=True)
def rollup(path: Path, config_file: str | None, verbose: bool) -> None:
    """Phase 4: Generate hierarchical directory and project summaries."""
    _setup_logging(verbose)
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.llm_client import LLMClient
    from repotalk.output import (
        load_file_docs,
        write_directory_summaries,
        write_project_summary,
    )
    from repotalk.rollup import rollup_all

    docs = load_file_docs(root, cfg)
    if not docs:
        console.print("[red]No file docs found. Run 'document' first.[/red]")
        sys.exit(1)

    client = LLMClient(cfg)
    console.print(
        f"[bold]Rolling up[/bold] {len(docs)} file docs with [cyan]{cfg.models.rollup_summaries}[/cyan]"
    )

    dir_summaries, project_summary = asyncio.run(rollup_all(docs, root, client, cfg))

    write_directory_summaries(dir_summaries, root, cfg)
    if project_summary:
        write_project_summary(project_summary, root, cfg)

    _print_cost_summary(client, "Rollup")


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-c", "--config", "config_file", type=click.Path(), default=None)
@click.option("-v", "--verbose", is_flag=True)
def run(path: Path, config_file: str | None, verbose: bool) -> None:
    """Run all phases in sequence: analyze -> document -> enrich -> rollup."""
    _setup_logging(verbose)
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.analyzer import analyze_file
    from repotalk.crawler import crawl
    from repotalk.documenter import document_all
    from repotalk.graph import KnowledgeGraph
    from repotalk.llm_client import LLMClient
    from repotalk.output import (
        load_hash_cache,
        save_hash_cache,
        write_analysis_cache,
        write_directory_summaries,
        write_file_docs,
        write_graph,
        write_project_summary,
    )
    from repotalk.rollup import rollup_all

    total_start = time.monotonic()
    client = LLMClient(cfg)

    # Phase 1: Analyze
    console.rule("[bold]Phase 1: Analyze[/bold]")
    files = crawl(root, cfg)
    console.print(f"Found [cyan]{len(files)}[/cyan] files")

    analyses = []
    for f in files:
        analyses.append(analyze_file(f, root))

    graph = KnowledgeGraph()
    graph.build_from_analyses(analyses)
    write_analysis_cache(analyses, root, cfg)
    write_graph(graph, root, cfg)
    console.print(f"[green]✓[/green] Analysis complete: {graph.stats()['total_nodes']} nodes")

    # Phase 2: Document
    console.rule("[bold]Phase 2: Document[/bold]")
    hash_cache = load_hash_cache(root, cfg)
    docs = asyncio.run(document_all(analyses, root, client, cfg, graph, hash_cache))
    write_file_docs(docs, root, cfg)
    save_hash_cache(hash_cache, root, cfg)
    console.print(f"[green]✓[/green] Documented {len(docs)} files")

    # Phase 3: Enrich
    console.rule("[bold]Phase 3: Enrich Graph[/bold]")
    asyncio.run(_enrich_graph(graph, client, cfg))
    write_graph(graph, root, cfg)
    console.print("[green]✓[/green] Graph enriched")

    # Phase 4: Rollup
    console.rule("[bold]Phase 4: Rollup[/bold]")
    dir_summaries, project_summary = asyncio.run(rollup_all(docs, root, client, cfg))
    write_directory_summaries(dir_summaries, root, cfg)
    if project_summary:
        write_project_summary(project_summary, root, cfg)
    console.print(f"[green]✓[/green] Generated {len(dir_summaries)} directory summaries")

    # Summary
    elapsed = time.monotonic() - total_start
    console.rule("[bold]Complete[/bold]")
    _print_cost_summary(client, "All Phases")
    console.print(f"Total time: [cyan]{elapsed:.1f}s[/cyan]")


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-c", "--config", "config_file", type=click.Path(), default=None)
@click.option("-v", "--verbose", is_flag=True)
def chat(path: Path, config_file: str | None, verbose: bool) -> None:
    """Interactive chat with your codebase documentation."""
    _setup_logging(verbose)
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.chat import ChatSession
    from repotalk.llm_client import LLMClient
    from repotalk.output import get_output_dir

    docs_dir = get_output_dir(root, cfg)
    if not docs_dir.exists():
        console.print("[red]No docs found. Run 'document' or 'run' first.[/red]")
        sys.exit(1)

    client = LLMClient(cfg)
    session = ChatSession(cfg, docs_dir, client)

    asyncio.run(session.run_repl())


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.argument("query")
@click.option("-c", "--config", "config_file", type=click.Path(), default=None)
@click.option("-k", "--top-k", type=int, default=None, help="Number of docs to retrieve")
@click.option("-o", "--output", "output_file", type=click.Path(), default=None, help="Output to file")
def context(
    path: Path,
    query: str,
    config_file: str | None,
    top_k: int | None,
    output_file: str | None,
) -> None:
    """Export relevant codebase context for a query (for external LLM use)."""
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.chat import export_context
    from repotalk.output import get_output_dir

    if top_k:
        cfg.chat.top_k = top_k

    docs_dir = get_output_dir(root, cfg)
    result = export_context(query, cfg, docs_dir)

    if output_file:
        Path(output_file).write_text(result)
        console.print(f"Context written to [cyan]{output_file}[/cyan]")
    else:
        console.print(result)


@cli.command()
@click.option("-c", "--config", "config_file", type=click.Path(), default=None, help="Config file path")
@click.option("-h", "--host", default="0.0.0.0", help="Host to bind to")
@click.option("-p", "--port", default=8420, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(config_file: str | None, host: str, port: int, reload: bool) -> None:
    """Start the RepoTalk web server (API + frontend)."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Install with: pip install repotalk[server][/red]")
        sys.exit(1)

    console.print(f"[bold]Starting RepoTalk server[/bold] on [cyan]{host}:{port}[/cyan]")
    console.print(f"  API:      http://localhost:{port}/api")
    console.print(f"  Health:   http://localhost:{port}/health")
    console.print(f"  Frontend: http://localhost:5173 (run 'cd web && npm run dev' separately)")
    console.print()

    if config_file:
        import os
        os.environ["REPOTALK_CONFIG"] = config_file

    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@cli.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("-c", "--config", "config_file", type=click.Path(), default=None)
def stats(path: Path, config_file: str | None) -> None:
    """Show codebase stats and estimated LLM costs."""
    cfg = _load_cfg(config_file, path)
    root = path.resolve()

    from repotalk.crawler import crawl

    files = crawl(root, cfg)

    total_lines = 0
    total_chars = 0
    for f in files:
        content = f.read_text(errors="replace")
        total_lines += content.count("\n") + 1
        total_chars += len(content)

    # Rough token estimate: ~4 chars per token
    est_tokens = total_chars // 4

    table = Table(title=f"Codebase Stats: {root.name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files", str(len(files)))
    table.add_row("Total lines", f"{total_lines:,}")
    table.add_row("Total characters", f"{total_chars:,}")
    table.add_row("Est. tokens (input)", f"{est_tokens:,}")
    table.add_row("", "")
    table.add_row("[bold]Estimated Costs[/bold]", "")
    table.add_row("  File docs (Gemini Flash)", f"${est_tokens * 2 * 0.15 / 1_000_000:.2f}")
    table.add_row("  File docs (GPT-4o-mini)", f"${est_tokens * 2 * 0.30 / 1_000_000:.2f}")
    table.add_row("  File docs (Claude Sonnet)", f"${est_tokens * 2 * 3.0 / 1_000_000:.2f}")
    table.add_row("  Rollup (est. 20% of input)", f"${est_tokens * 0.2 * 2 * 1.0 / 1_000_000:.2f}")
    console.print(table)

    console.print(
        "\n[dim]Cost estimates assume ~2x input tokens for combined input+output. "
        "Actual costs depend on model, output length, and provider pricing.[/dim]"
    )


def _print_cost_summary(client: "LLMClient", phase_name: str) -> None:
    """Print a cost summary table."""
    summary = client.cost_summary()

    table = Table(title=f"{phase_name} — Cost Summary")
    table.add_column("Phase", style="cyan")
    table.add_column("Calls", style="white")
    table.add_column("Input Tokens", style="white")
    table.add_column("Output Tokens", style="white")
    table.add_column("Cost", style="green")

    for phase, data in summary["phases"].items():
        table.add_row(
            phase,
            str(data["calls"]),
            f"{data['input_tokens']:,}",
            f"{data['output_tokens']:,}",
            f"${data['cost']:.4f}",
        )

    table.add_row(
        "[bold]Total[/bold]",
        "",
        f"{summary['total_input_tokens']:,}",
        f"{summary['total_output_tokens']:,}",
        f"[bold]${summary['total_cost']:.4f}[/bold]",
    )

    console.print(table)
