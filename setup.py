"""
Setup configuration for commit-reflect package.

This is the main package that users will install via pip.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="commit-reflect",
    version="0.1.0",
    author="Commit Reflect Team",
    author_email="contact@commit-reflect.dev",
    description="Developer experience micro-journaling system for commit reflections",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/commit-reflect",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/commit-reflect/issues",
        "Documentation": "https://github.com/yourusername/commit-reflect#readme",
        "Source Code": "https://github.com/yourusername/commit-reflect",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "packages"},
    packages=find_packages(where="packages"),
    python_requires=">=3.10",
    install_requires=[
        # Core dependencies for all components
        "click>=8.0",  # CLI framework
        "pydantic>=2.0",  # Data validation
        "rich>=13.0",  # Terminal formatting
    ],
    extras_require={
        "all": [
            "aiohttp>=3.8",  # MCP server
            "python-dateutil>=2.8",  # Date handling
        ],
        "mcp": [
            "aiohttp>=3.8",
            "python-dateutil>=2.8",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "ruff>=0.1.0",
            "mypy>=1.0",
            "pre-commit>=3.0",
        ],
        "docs": [
            "sphinx>=7.0",
            "sphinx-rtd-theme>=1.3",
            "sphinx-click>=5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "commit-reflect=cli.src.main:main",
            "mcp-commit-reflect=mcp_server.__main__:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yaml", "*.yml"],
    },
    zip_safe=False,
)
