from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mesh-os",
    version="0.1.9",
    author="Props",
    author_email="hello@props.app",
    description="A lightweight multi-agent memory system with semantic search",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Props-Labs/mesh-os",
    packages=find_packages(exclude=["tests*"]),
    package_data={
        "mesh_os": ["py.typed"],  # Include type information
        "mesh_os.templates": ["**/*"],  # Include all template files
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "openai>=1.0.0",
        "pydantic>=2.0.0",
        "requests>=2.25.0",
        "rich>=10.0.0",
        "python-dotenv>=0.19.0",
    ],
    entry_points={
        "console_scripts": [
            "mesh-os=mesh_os.cli.main:cli",
        ],
    },
) 