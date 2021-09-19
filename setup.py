from pathlib import Path

from setuptools import setup

long_description = (Path(__file__).parent / "README.md").read_text()

setup(
    name="pyopera",
    version="0.0.1.dev0",
    author="Panagiotis Karagiannis",
    author_email="papalotis1@gmail.com",
    description=("A personal project for visualizing opera visits."),
    license="MIT",
    keywords="opera website fastapi deta streamlit",
    url="https://github.com/papalotis/pyopera",
    packages=["pyopera"],
    long_description=long_description,
    install_requires=[
        "fastapi==0.68.1",
        "more-itertools==8.8.0",
        "Unidecode==1.2.0",
        "typing-extensions==3.10.0.0",
        "requests==2.26.0",
        "fastapi-utils==0.2.1",
        "deta==1.0.0",
        "plotly==5.3.1",
        "aiofiles==0.7.0",
    ],
)
