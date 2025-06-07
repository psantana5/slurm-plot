#!/usr/bin/env python3
"""
Data processor module for slurm-plot.

Handles processing and aggregation of SLURM job data into time series.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .config import get_config_value


class SlurmDataProcessor:
    """
    Processes and aggregates SLURM job data.
    """
    
    def __init__(self, config: Dict[str, Any], verbose: bool = False):
        """
        Initialize the data processor.
        
        Args:
            config: Configuration dictionary.
            verbose: Enable verbose output.
        """
        self.config = config
        self.verbose = verbose
        self.memory_unit = get_config_value(config, 'processing', 'memory_unit', 'GB')
        self.time_unit = get_config_value(config, 'processing', 'time_unit', 'hours')
        
    def process_data(self, raw_data: pd.DataFrame, interval: str = 'day') -> pd.DataFrame:
        """
        Process raw SLURM data into aggregated time series.
        
        Args:
            raw_data: Raw job data from fetcher.
            interval: Aggregation interval ('hour', 'day', 'week').
            
        Returns:
            Processed DataFrame with time series data.
        """
        if raw_data.empty:
            return pd.DataFrame()
            
        if self.verbose:
            print(f"Processing {len(raw_data)} job records...")
            
        # Clean and enrich the data
        df = self._enrich_job_data(raw_data.copy())
        
        if df.empty:
            return pd.DataFrame()
            
        # Aggregate by time interval
        aggregated = self._aggregate_by_interval(df, interval)
        
        if self.verbose:
            print(f"Aggregated into {len(aggregated)} time periods")
            
        return aggregated
        
    def _enrich_job_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrich job data with calculated fields.
        
        Args:
            df: Raw job DataFrame.
            
        Returns:
            Enriched DataFrame.
        """
        # Filter out invalid jobs
        df = df.dropna(subset=['Submit'])
        
        # Calculate derived fields
        df = self._calculate_times(df)
        df = self._calculate_resource_usage(df)
        df = self._calculate_efficiency_metrics(df)
        
        # Handle missing submit times
        missing_submit = df['Submit'].isna() | (df['Submit'] == 'Unknown')
        if missing_submit.any():
            # Use Start time as fallback for submit time
            df.loc[missing_submit, 'Submit'] = df.loc[missing_submit, 'Start']
            
        # Convert time columns to datetime
        df.loc[:, 'submit_time'] = pd.to_datetime(df['Submit'], errors='coerce')
        df.loc[:, 'start_time'] = pd.to_datetime(df['Start'], errors='coerce')
        df.loc[:, 'end_time'] = pd.to_datetime(df['End'], errors='coerce')
        
        # Create time grouping columns
        df.loc[:, 'submit_hour'] = df['submit_time'].dt.floor('h')
        df.loc[:, 'submit_day'] = df['submit_time'].dt.floor('D')
        df.loc[:, 'submit_week'] = df['submit_time'].dt.to_period('W').dt.start_time
        
        return df
        
    def _calculate_times(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate time-related metrics.
        
        Args:
            df: Job DataFrame.
            
        Returns:
            DataFrame with time metrics.
        """
        # Queue time (time between submit and start)
        df['queue_time_seconds'] = (df['Start'] - df['Submit']).dt.total_seconds()
        df['queue_time_hours'] = df['queue_time_seconds'] / 3600
        
        # Run time (time between start and end)
        df['run_time_seconds'] = (df['End'] - df['Start']).dt.total_seconds()
        df['run_time_hours'] = df['run_time_seconds'] / 3600
        
        # Handle negative or invalid times
        df['queue_time_hours'] = df['queue_time_hours'].clip(lower=0)
        df['run_time_hours'] = df['run_time_hours'].clip(lower=0)
        
        # Fill NaN values
        df['queue_time_hours'] = df['queue_time_hours'].fillna(0)
        df['run_time_hours'] = df['run_time_hours'].fillna(0)
        
        return df
        
    def _calculate_resource_usage(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate resource usage metrics.
        
        Args:
            df: Job DataFrame.
            
        Returns:
            DataFrame with resource usage metrics.
        """
        # CPU usage
        df['used_cpu_hours'] = df['CPUTimeRAW'] / 3600  # Convert seconds to hours
        df['allocated_cpu_hours'] = df['AllocCPUS'] * df['run_time_hours']
        
        # Memory usage (convert to GB if needed)
        if self.memory_unit == 'GB':
            # ReqMem and MaxRSS should already be in GB from fetcher
            df['req_mem_gb'] = df['ReqMem']
            df['max_rss_gb'] = df['MaxRSS']
        else:
            # Convert if needed
            df['req_mem_gb'] = df['ReqMem']
            df['max_rss_gb'] = df['MaxRSS']
            
        # GPU usage
        df['gpu_hours'] = df['GPUCount'] * df['run_time_hours']
        
        # Handle missing or invalid values
        numeric_cols = ['used_cpu_hours', 'allocated_cpu_hours', 'req_mem_gb', 'max_rss_gb', 'gpu_hours']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                df[col] = df[col].clip(lower=0)
                
        return df
        
    def _calculate_efficiency_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate efficiency metrics.
        
        Args:
            df: Job DataFrame.
            
        Returns:
            DataFrame with efficiency metrics.
        """
        # CPU efficiency
        df['cpu_efficiency'] = np.where(
            df['allocated_cpu_hours'] > 0,
            df['used_cpu_hours'] / df['allocated_cpu_hours'],
            0
        )
        df['cpu_efficiency'] = df['cpu_efficiency'].clip(upper=1.0)
        
        # Memory efficiency
        df['memory_efficiency'] = np.where(
            df['req_mem_gb'] > 0,
            df['max_rss_gb'] / df['req_mem_gb'],
            0
        )
        df['memory_efficiency'] = df['memory_efficiency'].clip(upper=1.0)
        
        return df
        
    def _aggregate_by_interval(self, df: pd.DataFrame, interval: str) -> pd.DataFrame:
        """
        Aggregate job data by time interval.
        
        Args:
            df: Enriched job DataFrame.
            interval: Time interval ('hour', 'day', 'week').
            
        Returns:
            Aggregated DataFrame.
        """
        # Select the appropriate time column
        time_col_map = {
            'hour': 'submit_hour',
            'day': 'submit_day',
            'week': 'submit_week'
        }
        
        if interval not in time_col_map:
            raise ValueError(f"Invalid interval: {interval}")
            
        time_col = time_col_map[interval]
        
        if time_col not in df.columns:
            raise ValueError(f"Time column {time_col} not found in data")
            
        # Group by time interval
        grouped = df.groupby(time_col)
        
        # Define aggregation functions
        agg_funcs = {
            # CPU metrics
            'ReqCPUS': 'sum',
            'AllocCPUS': 'sum', 
            'used_cpu_hours': 'sum',
            'allocated_cpu_hours': 'sum',
            
            # Memory metrics
            'req_mem_gb': 'sum',
            'max_rss_gb': 'sum',
            
            # GPU metrics
            'GPUCount': 'sum',
            'gpu_hours': 'sum',
            
            # Time metrics
            'queue_time_hours': 'mean',
            'run_time_hours': 'mean',
            
            # Efficiency metrics
            'cpu_efficiency': 'mean',
            'memory_efficiency': 'mean',
            
            # Job count
            'JobID': 'count'
        }
        
        # Perform aggregation
        result = grouped.agg(agg_funcs)
        
        # Rename columns to match expected metric names
        column_mapping = {
            'ReqCPUS': 'req_cpus',
            'AllocCPUS': 'alloc_cpus',
            'used_cpu_hours': 'used_cpus',
            'req_mem_gb': 'req_mem',
            'max_rss_gb': 'max_rss',
            'GPUCount': 'alloc_gpus',
            'gpu_hours': 'used_gpus',
            'queue_time_hours': 'queue_time',
            'run_time_hours': 'run_time',
            'JobID': 'job_count'
        }
        
        result = result.rename(columns=column_mapping)
        
        # Calculate additional derived metrics
        result['used_mem'] = result['max_rss']  # Alias for consistency
        
        # Ensure all expected columns exist
        expected_columns = [
            'req_cpus', 'alloc_cpus', 'used_cpus',
            'req_mem', 'max_rss', 'used_mem',
            'alloc_gpus', 'used_gpus',
            'queue_time', 'run_time', 'job_count'
        ]
        
        for col in expected_columns:
            if col not in result.columns:
                result[col] = 0
                
        # Fill any remaining NaN values
        result = result.fillna(0)
        
        # Sort by time index
        result = result.sort_index()
        
        return result
        
    def calculate_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate summary statistics for the processed data.
        
        Args:
            df: Processed DataFrame.
            
        Returns:
            Dictionary containing summary statistics.
        """
        if df.empty:
            return {}
            
        stats = {
            'total_jobs': int(df['job_count'].sum()),
            'total_cpu_hours_requested': float(df['req_cpus'].sum()),
            'total_cpu_hours_allocated': float(df['alloc_cpus'].sum()),
            'total_cpu_hours_used': float(df['used_cpus'].sum()),
            'total_memory_requested_gb': float(df['req_mem'].sum()),
            'total_memory_used_gb': float(df['max_rss'].sum()),
            'total_gpu_hours': float(df['used_gpus'].sum()),
            'avg_queue_time_hours': float(df['queue_time'].mean()),
            'avg_run_time_hours': float(df['run_time'].mean()),
            'date_range': {
                'start': df.index.min().isoformat() if not df.empty else None,
                'end': df.index.max().isoformat() if not df.empty else None
            }
        }
        
        # Calculate efficiency metrics
        if stats['total_cpu_hours_allocated'] > 0:
            stats['overall_cpu_efficiency'] = stats['total_cpu_hours_used'] / stats['total_cpu_hours_allocated']
        else:
            stats['overall_cpu_efficiency'] = 0.0
            
        if stats['total_memory_requested_gb'] > 0:
            stats['overall_memory_efficiency'] = stats['total_memory_used_gb'] / stats['total_memory_requested_gb']
        else:
            stats['overall_memory_efficiency'] = 0.0
            
        return stats
        
    def filter_data(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_job_count: int = 0
    ) -> pd.DataFrame:
        """
        Apply additional filters to processed data.
        
        Args:
            df: Processed DataFrame.
            start_date: Filter start date.
            end_date: Filter end date.
            min_job_count: Minimum job count per time period.
            
        Returns:
            Filtered DataFrame.
        """
        filtered_df = df.copy()
        
        # Filter by date range
        if start_date:
            filtered_df = filtered_df[filtered_df.index >= start_date]
        if end_date:
            filtered_df = filtered_df[filtered_df.index <= end_date]
            
        # Filter by minimum job count
        if min_job_count > 0:
            filtered_df = filtered_df[filtered_df['job_count'] >= min_job_count]
            
        return filtered_df