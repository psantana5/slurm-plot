#!/usr/bin/env python3
"""
CLI module for slurm-plot tool.

Handles command-line argument parsing and orchestrates the data extraction,
processing, and plotting workflow.
"""

import click
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from .fetcher import SlurmDataFetcher
from .processor import SlurmDataProcessor
from .plotter import SlurmPlotter
from .config import load_config


# Available metrics for plotting
AVAILABLE_METRICS = [
    "req_cpus", "alloc_cpus", "used_cpus",
    "req_mem", "max_rss", "used_mem",
    "alloc_gpus", "used_gpus",
    "queue_time", "run_time", "job_count"
]

# Available aggregation intervals
AVAILABLE_INTERVALS = ["hour", "day", "week"]

# Available output formats
AVAILABLE_FORMATS = ["png", "svg", "html"]

# Available job states
AVAILABLE_STATES = [
    "COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "RUNNING", "PENDING"
]


def validate_date(ctx, param, value):
    """Validate date format (YYYY-MM-DD)."""
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise click.BadParameter(f"Invalid date format: {value}. Use YYYY-MM-DD.")


def validate_metrics(ctx, param, value):
    """Validate metrics list."""
    if not value:
        return AVAILABLE_METRICS  # Default to all metrics
    
    invalid_metrics = [m for m in value if m not in AVAILABLE_METRICS]
    if invalid_metrics:
        raise click.BadParameter(
            f"Invalid metrics: {', '.join(invalid_metrics)}. "
            f"Available: {', '.join(AVAILABLE_METRICS)}"
        )
    return value


@click.command()
@click.option(
    "--start", "-s",
    callback=validate_date,
    help="Start date for data extraction (YYYY-MM-DD). Default: 7 days ago."
)
@click.option(
    "--end", "-e",
    callback=validate_date,
    help="End date for data extraction (YYYY-MM-DD). Default: today."
)
@click.option(
    "--account", "-A",
    help="Filter by SLURM account name."
)
@click.option(
    "--partition", "-p",
    help="Filter by SLURM partition name."
)
@click.option(
    "--state",
    type=click.Choice(AVAILABLE_STATES, case_sensitive=False),
    help="Filter by job state."
)
@click.option(
    "--user", "-u",
    help="Filter by username."
)
@click.option(
    "--interval", "-i",
    type=click.Choice(AVAILABLE_INTERVALS),
    default="day",
    help="Aggregation interval for time series data."
)
@click.option(
    "--metrics", "-m",
    multiple=True,
    callback=validate_metrics,
    help=f"Metrics to plot. Available: {', '.join(AVAILABLE_METRICS)}. "
         "Can be specified multiple times."
)
@click.option(
    "--output", "-o",
    default="slurm_plot",
    help="Output filename (without extension)."
)
@click.option(
    "--format", "-f",
    type=click.Choice(AVAILABLE_FORMATS),
    default="png",
    help="Output format for the plot."
)
@click.option(
    "--interactive",
    is_flag=True,
    help="Generate interactive HTML plot using Plotly."
)
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to configuration file."
)
@click.option(
    "--log-file",
    type=click.Path(),
    help="Path to SLURM log file (alternative to sacct)."
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output."
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without executing."
)
def main(
    start: Optional[datetime],
    end: Optional[datetime],
    account: Optional[str],
    partition: Optional[str],
    state: Optional[str],
    user: Optional[str],
    interval: str,
    metrics: List[str],
    output: str,
    format: str,
    interactive: bool,
    config: Optional[str],
    log_file: Optional[str],
    verbose: bool,
    dry_run: bool
):
    """SLURM Plot - Extract, process and visualize SLURM job data.
    
    This tool connects to SLURM using the sacct command (or log files) to extract
    job data, processes it into time series, and generates visualizations.
    
    Examples:
    
        # Plot CPU and memory usage for the last week
        slurm-plot --metrics req_cpus alloc_cpus req_mem max_rss
        
        # Generate interactive HTML plot for specific account
        slurm-plot --account myproject --interactive --format html
        
        # Analyze failed jobs in the last month
        slurm-plot --start 2024-01-01 --state FAILED --interval week
    """
    try:
        # Load configuration
        config_data = load_config(config)
        
        # Set default dates if not provided
        if end is None:
            end = datetime.now()
        if start is None:
            start = end - timedelta(days=7)
            
        if start >= end:
            click.echo("Error: Start date must be before end date.", err=True)
            sys.exit(1)
            
        # Override format if interactive is requested
        if interactive:
            format = "html"
            
        if verbose:
            click.echo(f"Configuration loaded from: {config or 'default'}")
            click.echo(f"Date range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
            click.echo(f"Metrics: {', '.join(metrics)}")
            click.echo(f"Interval: {interval}")
            click.echo(f"Output: {output}.{format}")
            
        if dry_run:
            click.echo("Dry run mode - no actual processing will be performed.")
            return
            
        # Initialize components
        fetcher = SlurmDataFetcher(config_data, verbose=verbose)
        processor = SlurmDataProcessor(config_data, verbose=verbose)
        plotter = SlurmPlotter(config_data, verbose=verbose)
        
        # Extract data
        if verbose:
            click.echo("Extracting SLURM data...")
            
        if log_file:
            raw_data = fetcher.fetch_from_log_file(log_file, start, end)
        else:
            raw_data = fetcher.fetch_from_sacct(
                start=start,
                end=end,
                account=account,
                partition=partition,
                state=state,
                user=user
            )
            
        if raw_data.empty:
            click.echo("No data found for the specified criteria.", err=True)
            sys.exit(1)
            
        if verbose:
            click.echo(f"Found {len(raw_data)} job records.")
            
        # Process data
        if verbose:
            click.echo("Processing and aggregating data...")
            
        processed_data = processor.process_data(raw_data, interval)
        
        if processed_data.empty:
            click.echo("No data to plot after processing.", err=True)
            sys.exit(1)
            
        # Generate plot
        if verbose:
            click.echo(f"Generating {format.upper()} plot...")
            
        output_path = plotter.create_plot(
            data=processed_data,
            metrics=metrics,
            output_file=f"{output}.{format}",
            format=format,
            interactive=interactive,
            title=f"SLURM Job Metrics ({start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')})"
        )
        
        click.echo(f"Plot saved to: {output_path}")
        
        # Print summary statistics
        if verbose:
            total_jobs = processed_data['job_count'].sum()
            date_range = f"{processed_data.index.min()} to {processed_data.index.max()}"
            click.echo(f"\nSummary:")
            click.echo(f"  Total jobs: {total_jobs:,}")
            click.echo(f"  Date range: {date_range}")
            click.echo(f"  Aggregation: {interval}")
            click.echo(f"  Metrics plotted: {len(metrics)}")
            
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()