"""
Setup script for bridgesec-logging package.

This allows the logging package to be installed in other projects:
    pip install -e ../bridgesec-data-transformer
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read version from __init__.py
init_file = Path(__file__).parent / 'bridgesec_logging' / '__init__.py'
version = '1.0.0'
for line in init_file.read_text().splitlines():
    if line.startswith('__version__'):
        version = line.split('=')[1].strip().strip('"').strip("'")
        break

# Read README if it exists
readme_file = Path(__file__).parent / 'README.md'
long_description = ''
if readme_file.exists():
    long_description = readme_file.read_text()

setup(
    name="bridgesec-logging",
    version=version,
    description="Centralized structured logging for BridgeSec microservices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="BridgeSec Team",
    author_email="admin@bridgesec.com",
    url="https://github.com/bridgesec/bridgesec-data-transformer",
    packages=['bridgesec_logging'],
    install_requires=[
        "python-json-logger==2.0.7",
        "python-logging-loki==0.3.1",
    ],
    extras_require={
        'django': [
            'django>=4.0',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="logging loki grafana structured-logging microservices",
)
