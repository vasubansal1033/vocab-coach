from vocab.cli import main


def test_cli_runs_without_command() -> None:
    assert main([]) == 0
