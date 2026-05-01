#!/usr/bin/env python3
"""
Setup script for API Discovery & Auth Service.
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="api-discovery-service",
    version="1.0.0",
    author="API Discovery Team",
    author_email="team@api-discovery.dev",
    description="The missing link between AI app builders and the real world",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/api-discovery-auth-service",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.11",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
        ],
        "docs": [
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.4.8",
            "mkdocs-mermaid2-plugin>=1.1.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "api-discovery=gallely.cli:main",
            "api-discovery-server=gallely.api.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "gallely": [
            "templates/*.html",
            "static/*",
            "config/*.yaml"
        ],
    },
    keywords=[
        "api", "discovery", "authentication", "ai", "llm", "automation",
        "browser", "tavily", "openai", "fastapi", "async"
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/api-discovery-auth-service/issues",
        "Source": "https://github.com/yourusername/api-discovery-auth-service",
        "Documentation": "https://docs.api-discovery.dev",
    },
) 