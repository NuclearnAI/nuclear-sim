"""
Setup configuration for GSE GPWR Python library.
"""

from setuptools import setup, find_packages

with open("gse/README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gse-gpwr",
    version="1.0.0",
    author="Nuclear Sim Team",
    description="Python library for GSE GPWR nuclear simulator via ONC RPC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.10",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
