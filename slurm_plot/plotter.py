#!/usr/bin/env python3
"""
Plotting module for slurm-plot.

Handles generation of visualizations for SLURM job data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

def _import_matplotlib():
    """Import matplotlib modules when needed."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        return plt, mdates
    except ImportError:
        raise ImportError("matplotlib is required for plotting. Install with: pip install matplotlib")

from .config import get_config_value


class SlurmPlotter:
    """
    Creates visualizations for SLURM job data.
    """
    
    def __init__(self, config: Dict[str, Any], verbose: bool = False):
        """
        Initialize the plotter.
        
        Args:
            config: Configuration dictionary.
            verbose: Enable verbose output.
        """
        self.config = config
        self.verbose = verbose
        
        # Load plotting configuration
        self.figure_width = get_config_value(config, 'plotting', 'figure_width', 12)
        self.figure_height = get_config_value(config, 'plotting', 'figure_height', 8)
        self.dpi = get_config_value(config, 'plotting', 'dpi', 300)
        self.style = get_config_value(config, 'plotting', 'style', 'seaborn-v0_8')
        self.color_palette = get_config_value(config, 'plotting', 'color_palette', 'tab10')
        self.grid = get_config_value(config, 'plotting', 'grid', True)
        self.legend = get_config_value(config, 'plotting', 'legend', True)
        
        # Load output configuration
        self.quality = get_config_value(config, 'output', 'quality', 95)
        self.transparent = get_config_value(config, 'output', 'transparent', False)
        
        # Set matplotlib style
        try:
            plt, _ = _import_matplotlib()
            plt.style.use(self.style)
        except OSError:
            if self.verbose:
                print(f"Warning: Style '{self.style}' not available, using default")
            plt.style.use('default')
        except ImportError:
            if self.verbose:
                print("Warning: matplotlib not available, some plotting features will be disabled")
            
    def create_plot(
        self,
        data: pd.DataFrame,
        metrics: List[str],
        output_file: str,
        format: str = 'png',
        interactive: bool = False,
        title: Optional[str] = None
    ) -> str:
        """
        Create a plot for the specified metrics.
        
        Args:
            data: Processed job data.
            metrics: List of metrics to plot.
            output_file: Output file path.
            format: Output format ('png', 'pdf', 'svg', 'html').
            interactive: Whether to create interactive plot.
            title: Optional plot title.
            
        Returns:
            Path to the created plot file.
        """
        if interactive or format == 'html':
            return self._create_interactive_plot(data, metrics, output_file, title)
        else:
            return self._create_static_plot(data, metrics, output_file, format, title)
            
    def _create_static_plot(
        self,
        data: pd.DataFrame,
        metrics: List[str],
        output_file: str,
        format: str,
        title: Optional[str]
    ) -> str:
        """
        Create a static plot using matplotlib.
        
        Args:
            data: Time series data.
            metrics: Metrics to plot.
            output_file: Output file path.
            format: Output format.
            title: Plot title.
            
        Returns:
            Path to the created plot file.
        """
        plt, mdates = _import_matplotlib()
        
        # Group metrics by type for better visualization
        metric_groups = self._group_metrics(metrics)
        
        # Calculate number of subplots needed
        n_groups = len(metric_groups)
        if n_groups == 0:
            raise ValueError("No valid metrics to plot")
            
        # Create figure with subplots
        fig, axes = plt.subplots(
            n_groups, 1,
            figsize=(self.figure_width, self.figure_height * n_groups / 2),
            dpi=self.dpi,
            squeeze=False
        )
        
        # Set overall title
        if title:
            fig.suptitle(title, fontsize=16, fontweight='bold')
            
        # Plot each group
        for i, (group_name, group_metrics) in enumerate(metric_groups.items()):
            ax = axes[i, 0]
            self._plot_metric_group(ax, data, group_metrics, group_name)
            
        # Adjust layout
        plt.tight_layout()
        if title:
            plt.subplots_adjust(top=0.95)
            
        # Save the plot
        output_path = Path(output_file)
        save_kwargs = {
            'dpi': self.dpi,
            'bbox_inches': 'tight',
            'transparent': self.transparent
        }
        
        if format.lower() in ['jpg', 'jpeg', 'png']:
            save_kwargs['quality'] = self.quality
            
        plt.savefig(output_path, format=format, **save_kwargs)
        plt.close()
        
        return str(output_path.absolute())
        
    def _create_interactive_plot(
        self,
        data: pd.DataFrame,
        metrics: List[str],
        output_file: str,
        title: Optional[str]
    ) -> str:
        """
        Create an interactive plot using Plotly.
        
        Args:
            data: Time series data.
            metrics: Metrics to plot.
            output_file: Output file path.
            title: Plot title.
            
        Returns:
            Path to the created HTML file.
        """
        if not PLOTLY_AVAILABLE:
            raise RuntimeError("Plotly is not available. Install with: pip install plotly")
            
        # Group metrics by type
        metric_groups = self._group_metrics(metrics)
        n_groups = len(metric_groups)
        
        if n_groups == 0:
            raise ValueError("No valid metrics to plot")
            
        # Create subplots
        subplot_titles = list(metric_groups.keys())
        fig = make_subplots(
            rows=n_groups,
            cols=1,
            subplot_titles=subplot_titles,
            vertical_spacing=0.1
        )
        
        # Color palette
        colors = plt.cm.get_cmap(self.color_palette)(np.linspace(0, 1, 10))
        color_hex = ['#%02x%02x%02x' % (int(r*255), int(g*255), int(b*255)) for r, g, b, _ in colors]
        
        # Plot each group
        for i, (group_name, group_metrics) in enumerate(metric_groups.items()):
            for j, metric in enumerate(group_metrics):
                if metric in data.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=data.index,
                            y=data[metric],
                            mode='lines+markers',
                            name=self._get_metric_label(metric),
                            line=dict(color=color_hex[j % len(color_hex)]),
                            hovertemplate=f'<b>{self._get_metric_label(metric)}</b><br>' +
                                        'Date: %{x}<br>' +
                                        'Value: %{y:.2f}<br>' +
                                        '<extra></extra>'
                        ),
                        row=i+1,
                        col=1
                    )
                    
        # Update layout
        fig.update_layout(
            title=title or "SLURM Job Metrics",
            height=400 * n_groups,
            showlegend=True,
            hovermode='x unified'
        )
        
        # Update x-axes
        for i in range(n_groups):
            fig.update_xaxes(
                title_text="Date" if i == n_groups - 1 else "",
                row=i+1,
                col=1
            )
            
        # Save as HTML
        output_path = Path(output_file)
        if output_path.suffix.lower() != '.html':
            output_path = output_path.with_suffix('.html')
            
        pyo.plot(fig, filename=str(output_path), auto_open=False)
        
        return str(output_path.absolute())
        
    def _group_metrics(self, metrics: List[str]) -> Dict[str, List[str]]:
        """
        Group metrics by type for better visualization.
        
        Args:
            metrics: List of metric names.
            
        Returns:
            Dictionary mapping group names to metric lists.
        """
        groups = {
            'CPU Metrics': [],
            'Memory Metrics': [],
            'GPU Metrics': [],
            'Time Metrics': [],
            'Job Count': []
        }
        
        for metric in metrics:
            if metric in ['req_cpus', 'alloc_cpus', 'used_cpus']:
                groups['CPU Metrics'].append(metric)
            elif metric in ['req_mem', 'max_rss', 'used_mem']:
                groups['Memory Metrics'].append(metric)
            elif metric in ['alloc_gpus', 'used_gpus']:
                groups['GPU Metrics'].append(metric)
            elif metric in ['queue_time', 'run_time']:
                groups['Time Metrics'].append(metric)
            elif metric == 'job_count':
                groups['Job Count'].append(metric)
                
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
        
    def _plot_metric_group(
        self,
        ax,
        data: pd.DataFrame,
        metrics: List[str],
        group_name: str
    ) -> None:
        """
        Plot a group of related metrics on the same axes.
        
        Args:
            ax: Matplotlib axes object.
            data: Time series data.
            metrics: Metrics to plot in this group.
            group_name: Name of the metric group.
        """
        plt, mdates = _import_matplotlib()
        
        # Get color palette
        colors = plt.cm.get_cmap(self.color_palette)(np.linspace(0, 1, len(metrics)))
        
        # Plot each metric
        for i, metric in enumerate(metrics):
            if metric in data.columns:
                ax.plot(
                    data.index,
                    data[metric],
                    label=self._get_metric_label(metric),
                    color=colors[i],
                    linewidth=2,
                    marker='o',
                    markersize=4
                )
                
        # Customize axes
        ax.set_title(group_name, fontsize=14, fontweight='bold')
        ax.set_ylabel(self._get_group_ylabel(group_name))
        
        if self.grid:
            ax.grid(True, alpha=0.3)
            
        if self.legend and len(metrics) > 1:
            ax.legend(loc='best')
            
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(data) // 10)))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
    def _get_metric_label(self, metric: str) -> str:
        """
        Get a human-readable label for a metric.
        
        Args:
            metric: Metric name.
            
        Returns:
            Human-readable label.
        """
        labels = {
            'req_cpus': 'Requested CPUs',
            'alloc_cpus': 'Allocated CPUs',
            'used_cpus': 'Used CPU Hours',
            'req_mem': 'Requested Memory (GB)',
            'max_rss': 'Max Memory Used (GB)',
            'used_mem': 'Used Memory (GB)',
            'alloc_gpus': 'Allocated GPUs',
            'used_gpus': 'GPU Hours',
            'queue_time': 'Queue Time (hours)',
            'run_time': 'Run Time (hours)',
            'job_count': 'Job Count'
        }
        return labels.get(metric, metric.replace('_', ' ').title())
        
    def _get_group_ylabel(self, group_name: str) -> str:
        """
        Get appropriate y-axis label for a metric group.
        
        Args:
            group_name: Name of the metric group.
            
        Returns:
            Y-axis label.
        """
        labels = {
            'CPU Metrics': 'CPU Count / Hours',
            'Memory Metrics': 'Memory (GB)',
            'GPU Metrics': 'GPU Count / Hours',
            'Time Metrics': 'Time (hours)',
            'Job Count': 'Number of Jobs'
        }
        return labels.get(group_name, 'Value')
        
    def create_summary_report(
        self,
        data: pd.DataFrame,
        stats: Dict[str, Any],
        output_file: str
    ) -> str:
        """
        Create a summary report with key statistics.
        
        Args:
            data: Processed time series data.
            stats: Summary statistics.
            output_file: Output file path.
            
        Returns:
            Path to the created report file.
        """
        output_path = Path(output_file)
        
        with open(output_path, 'w') as f:
            f.write("# SLURM Job Analysis Report\n\n")
            
            # Summary statistics
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Jobs**: {stats.get('total_jobs', 0):,}\n")
            f.write(f"- **Date Range**: {stats.get('date_range', {}).get('start', 'N/A')} to {stats.get('date_range', {}).get('end', 'N/A')}\n")
            f.write(f"- **Total CPU Hours Requested**: {stats.get('total_cpu_hours_requested', 0):,.1f}\n")
            f.write(f"- **Total CPU Hours Used**: {stats.get('total_cpu_hours_used', 0):,.1f}\n")
            f.write(f"- **CPU Efficiency**: {stats.get('overall_cpu_efficiency', 0):.1%}\n")
            f.write(f"- **Total Memory Requested**: {stats.get('total_memory_requested_gb', 0):,.1f} GB\n")
            f.write(f"- **Total Memory Used**: {stats.get('total_memory_used_gb', 0):,.1f} GB\n")
            f.write(f"- **Memory Efficiency**: {stats.get('overall_memory_efficiency', 0):.1%}\n")
            f.write(f"- **Total GPU Hours**: {stats.get('total_gpu_hours', 0):,.1f}\n")
            f.write(f"- **Average Queue Time**: {stats.get('avg_queue_time_hours', 0):.1f} hours\n")
            f.write(f"- **Average Run Time**: {stats.get('avg_run_time_hours', 0):.1f} hours\n")
            
            # Data table
            f.write("\n## Time Series Data\n\n")
            f.write(data.to_markdown())
            
        return str(output_path.absolute())