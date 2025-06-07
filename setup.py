#!/usr/bin/env python3
"""
Setup script for slurm-plot CLI tool.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="slurm-plot",
    version="1.0.0",
    author="SLURM Plot Team",
    author_email="contact@slurmplot.com",
    description="A CLI tool for extracting, processing and plotting SLURM job data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/slurmplot/slurm-plot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Monitoring",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "slurm-plot=slurm_plot.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "slurm_plot": ["config/*.ini"],
    },
)