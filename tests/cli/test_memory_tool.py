# -*- coding: utf-8 -*-
"""Tests for LitePaw memory_tool CLI."""

import tempfile
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from litepaw.memory_tool import cli


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def workspace_with_files():
    """Create a temporary workspace with memory files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        memory_dir = workspace / "memory"
        memory_dir.mkdir()

        (workspace / "MEMORY.md").write_text("# My Memory\n- User likes Python\n- Prefers async", encoding="utf-8")
        (memory_dir / "2026-08-01.md").write_text("# Day 1\nTalked about AI", encoding="utf-8")
        (memory_dir / "2026-08-02.md").write_text("# Day 2\nDiscussed deployment", encoding="utf-8")

        yield workspace


class TestCLIExport:
    """Tests for export command."""

    def test_T1_export_empty_workspace(self, runner):
        """T1: Export with no memory files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ["--workspace", tmpdir, "export", "out.zip"])
            assert result.exit_code == 0
            assert "No memory files found" in result.output

    def test_T2_export_with_files(self, runner, workspace_with_files):
        """T2: Export creates ZIP with memory files."""
        out_zip = str(workspace_with_files / "out.zip")
        result = runner.invoke(cli, [
            "--workspace", str(workspace_with_files),
            "export", out_zip,
        ])
        assert result.exit_code == 0
        assert "Exported 3 files" in result.output

        # Verify ZIP contents
        assert Path(out_zip).exists()
        with zipfile.ZipFile(out_zip, "r") as zf:
            names = zf.namelist()
            assert "MEMORY.md" in names
            assert "memory/2026-08-01.md" in names
            assert "memory/2026-08-02.md" in names


class TestCLIImport:
    """Tests for import command."""

    def test_T3_import_new_files(self, runner):
        """T3: Import creates new files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            zip_path = str(workspace / "import.zip")

            # Create ZIP
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("MEMORY.md", "# Imported\n- New content")
                zf.writestr("memory/2026-08-03.md", "# Day 3")

            result = runner.invoke(cli, [
                "--workspace", str(workspace),
                "import-memory", zip_path,
            ])
            assert result.exit_code == 0
            assert "Imported 2 files" in result.output

            # Verify files
            assert (workspace / "MEMORY.md").read_text(encoding="utf-8") == "# Imported\n- New content"
            assert (workspace / "memory/2026-08-03.md").read_text(encoding="utf-8") == "# Day 3"

    def test_T4_import_merge_skips_existing(self, runner, workspace_with_files):
        """T4: Import merge skips existing files."""
        zip_path = str(workspace_with_files / "import.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            # MEMORY.md already exists
            zf.writestr("MEMORY.md", "# Should be skipped")
            # New file
            zf.writestr("memory/2026-08-03.md", "# Day 3")

        result = runner.invoke(cli, [
            "--workspace", str(workspace_with_files),
            "import-memory", zip_path,
        ])
        assert result.exit_code == 0
        # MEMORY.md should be skipped, only 1 new file imported
        assert "Skipping existing file: MEMORY.md" in result.output
        assert "Imported 1 files" in result.output

    def test_T5_import_overwrite(self, runner, workspace_with_files):
        """T5: Import overwrite mode overwrites existing files."""
        zip_path = str(workspace_with_files / "import.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("MEMORY.md", "# Overwritten")

        result = runner.invoke(cli, [
            "--workspace", str(workspace_with_files),
            "--daily-dir", "memory",
            "import-memory", zip_path,
            "--overwrite",
        ])
        assert result.exit_code == 0
        assert "Imported 1 files" in result.output
        assert (workspace_with_files / "MEMORY.md").read_text(encoding="utf-8") == "# Overwritten"


class TestCLIList:
    """Tests for list command."""

    def test_T6_list_empty_workspace(self, runner):
        """T6: List on empty workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(cli, ["--workspace", tmpdir, "list-memory"])
            assert result.exit_code == 0
            assert "No memory files found" in result.output

    def test_T7_list_with_files(self, runner, workspace_with_files):
        """T7: List shows files with sizes."""
        result = runner.invoke(cli, [
            "--workspace", str(workspace_with_files),
            "--daily-dir", "memory",
            "list-memory",
        ])
        assert result.exit_code == 0
        assert "Found 3 memory files" in result.output
        assert "MEMORY.md" in result.output
        assert "memory/2026-08-01.md" in result.output
        assert "memory/2026-08-02.md" in result.output
        assert "bytes" in result.output.lower() or "bytes" in result.output


class TestCLISearch:
    """Tests for search command."""

    def test_T8_search_match(self, runner, workspace_with_files):
        """T8: Search finds matching lines."""
        result = runner.invoke(cli, [
            "--workspace", str(workspace_with_files),
            "--daily-dir", "memory",
            "search-memory", "Python",
        ])
        assert result.exit_code == 0
        assert "Found 1 matches for 'Python'" in result.output
        assert "MEMORY.md" in result.output
        assert "User likes Python" in result.output

    def test_T9_search_no_match(self, runner, workspace_with_files):
        """T9: Search with no matches."""
        result = runner.invoke(cli, [
            "--workspace", str(workspace_with_files),
            "--daily-dir", "memory",
            "search-memory", "nonexistent_keyword_xyz",
        ])
        assert result.exit_code == 0
        assert "No matches found" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
