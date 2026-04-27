"""Command-line interface for retryctl."""

from __future__ import annotations

import sys

import click

from retryctl.formatter import OutputFormat, format_result
from retryctl.runner import build_executor, run_command


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("command", nargs=-1, required=True)
@click.option(
    "--max-attempts",
    default=3,
    show_default=True,
    help="Maximum number of execution attempts.",
)
@click.option(
    "--strategy",
    default="exponential",
    show_default=True,
    type=click.Choice(["fixed", "linear", "exponential"], case_sensitive=False),
    help="Backoff strategy between retries.",
)
@click.option(
    "--base-delay",
    default=1.0,
    show_default=True,
    help="Base delay in seconds between retries.",
)
@click.option(
    "--max-delay",
    default=60.0,
    show_default=True,
    help="Maximum delay in seconds between retries.",
)
@click.option(
    "--retry-on",
    multiple=True,
    type=int,
    metavar="CODE",
    help="Exit code(s) that trigger a retry (default: any non-zero).",
)
@click.option(
    "--output",
    default="text",
    show_default=True,
    type=click.Choice(["text", "json", "quiet"], case_sensitive=False),
    help="Output format for execution summary.",
)
def main(
    command: tuple[str, ...],
    max_attempts: int,
    strategy: str,
    base_delay: float,
    max_delay: float,
    retry_on: tuple[int, ...],
    output: str,
) -> None:
    """Wrap COMMAND with configurable retry logic and backoff strategies."""
    executor = build_executor(
        max_attempts=max_attempts,
        strategy=strategy,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on_codes=list(retry_on) if retry_on else None,
    )
    result = run_command(executor, list(command))

    fmt = OutputFormat(output.lower())
    summary = format_result(result, fmt)
    if summary:
        click.echo(summary)

    sys.exit(result.exit_code)
