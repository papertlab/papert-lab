import re
from pathlib import Path

from setuptools import find_packages, setup

from papertlab import __version__


def get_requirements(suffix=""):
    if suffix:
        fname = "requirements-" + suffix + ".txt"
        fname = Path("requirements") / fname
    else:
        fname = Path("requirements.txt")

    requirements = fname.read_text().splitlines()

    return requirements


requirements = get_requirements() 

# README
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
    long_description = re.sub(r"\n!\[.*\]\(.*\)", "", long_description)

# Discover packages, plus the website
packages = find_packages(exclude=["benchmark", "tests"])
print("Packages:", packages)

setup(
    name="papert-lab",
    version=__version__,
    packages=packages,
    include_package_data=True,
    package_data={
        "papertlab": [
            "queries/*.scm",
            "static/*",
            "static/**/*",
            "static/**/**/*",
            "static/**/**/**/*",
            "templates/*",
        ],
    },
    install_requires=requirements,
    python_requires=">=3.7,<3.13",
    entry_points={
        "console_scripts": [
            "papertlab = papertlab.main:main",
        ],
    },
    description="papertlab is an AI pair programmer in your browser.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://papert.in/",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python",
        "Topic :: Software Development",
    ],
)
