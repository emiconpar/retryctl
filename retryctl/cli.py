"""CLI entry-point for retryctl."""

import sys
from typing import List

import click

from retryctl.runner import run_command


@click.command(context_settings={"ignore_unknown_options": True})
@click.option("--attempts", default=3, show_default=True, help="Maximum retry attempts.")
@click.option("--strategy", default="exponential", show_default=True,
              type=click.Choice(["fixed", "linear", "exponential"]),
              help="Backoff strategy.")
@click.option("--base-delay", default=1.0, show_default=True, help="Base delay in seconds.")
@click.option("--max-delay", default=60.0, show_default=True, help="Maximum delay in seconds.")
@click.option("--multiplier", default=2.0, show_default=True, help="Multiplier for exponential backoff.")
@click.option("--jitter", is_flag=True, default=False, help="Add random jitter to delays.")
@click.option("--timeout", default=None, type=float, help="Per-attempt timeout in seconds.")
@click.option("--retry-on", "retry_on_codes", default="", help="Comma-separated exit codes to retry on.")
@click.option("--stop-on", "stop_on_codes", default="", help="Comma-separated exit codes to stop on.")
@click.argument("command", nargs=-1, required=True)
def main(
    attempts: int,
    strategy: str,
    base_delay: float,
    max_delay: float,
    multiplier: float,
    jitter: bool,
    timeout,
    retry_on_codes: str,
    stop_on_codes: str,
    command,
) -> None:
    """Wrap COMMAND with retry logic and configurable backoff."""
    retry_codes = [int(c) for c in retry_on_codes.split(",") if c.strip()]
    stop_codes = [int(c) for c in stop_on_codes.split(",") if c.strip()]

    result = run_command(
        list(command),
        strategy=strategy,
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier,
        jitter=jitter,
        max_attempts=attempts,
        retry_on_codes=retry_codes,
        stop_on_codes=stop_codes,
        timeout=timeout,
    )

    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, nl=False, err=True)

    status = "succeeded" if result.succeeded else "failed"
    click.echo(
        f"[retryctl] command {status} after {result.attempts} attempt(s) "
        f"in {result.elapsed:.2f}s (exit code {result.returncode})",
        err=True,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
