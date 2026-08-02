# -*- coding: utf-8 -*-
"""CLI tool for memory export/import operations."""

import json
import zipfile
from pathlib import Path

import click

from litepaw.config.settings import Settings


def collect_memory_files(workspace: Path, daily_dir: str) -> dict[str, str]:
    """Collect all memory files from workspace."""
    result = {}

    memory_md = workspace / "MEMORY.md"
    if memory_md.exists():
        result["MEMORY.md"] = memory_md.read_text(encoding="utf-8")

    daily = workspace / daily_dir
    if daily.exists():
        for md_file in daily.glob("*.md"):
            rel = f"{daily_dir}/{md_file.name}"
            result[rel] = md_file.read_text(encoding="utf-8")

    meta = workspace / "mem_metadata"
    if meta.exists():
        for f in meta.rglob("*"):
            if f.is_file():
                rel = f"mem_metadata/{f.relative_to(meta)}"
                result[rel] = f.read_text(encoding="utf-8", errors="replace")

    return result


@click.group()
@click.option("--workspace", default="./workspace", help="Memory workspace root")
@click.option("--daily-dir", default="memory", help="Daily memory subdirectory")
@click.pass_context
def cli(ctx, workspace, daily_dir):
    """LitePaw memory export/import tool."""
    ctx.ensure_object(dict)
    ctx.obj["workspace"] = Path(workspace)
    ctx.obj["daily_dir"] = daily_dir


@cli.command()
@click.argument("output", type=click.Path())
@click.pass_context
def export(ctx, output):
    """Export memory files to a ZIP archive."""
    workspace: Path = ctx.obj["workspace"]
    daily_dir: str = ctx.obj["daily_dir"]

    if not workspace.exists():
        click.echo(f"Error: workspace '{workspace}' does not exist")
        return

    memory_files = collect_memory_files(workspace, daily_dir)
    if not memory_files:
        click.echo("No memory files found")
        return

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in memory_files.items():
            zf.writestr(rel_path, content)

    click.echo(f"Exported {len(memory_files)} files to {output_path}")


@cli.command(name="import-memory")
@click.argument("input_zip", type=click.Path(exists=True))
@click.option("--merge/--overwrite", default=True, help="Merge with existing files (default: merge)")
@click.pass_context
def import_(ctx, input_zip, merge):
    """Import memory files from a ZIP archive."""
    workspace: Path = ctx.obj["workspace"]
    workspace.mkdir(parents=True, exist_ok=True)

    imported = 0
    with zipfile.ZipFile(input_zip, "r") as zf:
        for name in zf.namelist():
            target = workspace / name
            if merge and target.exists():
                click.echo(f"Skipping existing file: {name}")
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            content = zf.read(name).decode("utf-8")
            target.write_text(content, encoding="utf-8")
            imported += 1

    click.echo(f"Imported {imported} files to {workspace}")


@cli.command(name="list-memory")
@click.pass_context
def list_(ctx):
    """List all memory files."""
    workspace: Path = ctx.obj["workspace"]
    daily_dir: str = ctx.obj["daily_dir"]

    if not workspace.exists():
        click.echo(f"Error: workspace '{workspace}' does not exist")
        return

    files = collect_memory_files(workspace, daily_dir)
    if not files:
        click.echo("No memory files found")
        return

    click.echo(f"Found {len(files)} memory files:")
    for name in sorted(files.keys()):
        size = len(files[name].encode("utf-8"))
        click.echo(f"  {name} ({size} bytes)")


@cli.command(name="search-memory")
@click.argument("query")
@click.option("--max-results", default=10, help="Max results to show")
@click.pass_context
def search(ctx, query, max_results):
    """Search memory files (keyword-based, no embedding required)."""
    workspace: Path = ctx.obj["workspace"]
    daily_dir: str = ctx.obj["daily_dir"]

    if not workspace.exists():
        click.echo(f"Error: workspace '{workspace}' does not exist")
        return

    memory_files = collect_memory_files(workspace, daily_dir)
    query_lower = query.lower()

    results = []
    for rel_path, content in memory_files.items():
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if query_lower in line.lower():
                start = max(0, i - 2)
                end = min(len(lines), i + 2)
                context = "\n".join(lines[start:end])
                results.append({
                    "file": rel_path,
                    "line": i,
                    "match": line.strip(),
                    "context": context,
                })

    if not results:
        click.echo("No matches found")
        return

    click.echo(f"Found {len(results)} matches for '{query}':")
    for r in results[:max_results]:
        click.echo(f"\n--- {r['file']}:{r['line']}")
        click.echo(r["context"])


if __name__ == "__main__":
    cli()
