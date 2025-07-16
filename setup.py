from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="poechatsaver",
    version="1.0.0",
    author="PoeChat Saver",
    description="A tool to save Poe.com shared conversations as markdown files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0", 
        "markdownify>=0.11.0",
        "click>=8.1.0",
        "lxml>=4.9.0",
        "urllib3>=2.0.0",
        "selenium>=4.15.0",
    ],
    entry_points={
        "console_scripts": [
            "poesaver=src.cli:main",
        ],
    },
) 