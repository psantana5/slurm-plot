#!/usr/bin/env python3
"""
SLURM Plot - A CLI tool for extracting, processing and plotting SLURM job data.

This package provides functionality to:
- Extract data from SLURM using sacct command
- Process and aggregate job metrics
- Generate visualizations and reports
- Export data in various formats
"""

__version__ = "1.0.0"
__author__ = "SLURM Plot Team"
__email__ = "contact@slurmplot.com"

# Import main modules for easier access
from .cli import main as cli_main
from .fetcher import SlurmDataFetcher
from .processor import SlurmDataProcessor
from .plotter import SlurmPlotter

__all__ = [
    "cli_main",
    "SlurmDataFetcher",
    "SlurmDataProcessor",
    "SlurmPlotter",
]