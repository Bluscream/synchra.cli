import pytest
from synchra_cli.main import entry_point

def test_cli_entry_point():
    """Ensure the CLI entry point is callable."""
    assert callable(entry_point)
