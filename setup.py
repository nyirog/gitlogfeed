#!/usr/bin/env python3
from setuptools import setup

with open("README.md") as fp:
    long_description = fp.read()

setup(
    name="gitlogfeed",
    version="0.2.0",
    description="Create an atom feed from git log",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Apache 2",
    python_requires='>=3.6',
    py_modules=["gitlogfeed"],
    entry_points = {
        'console_scripts': ['gitlogfeed=gitlogfeed:main'],
    },
    url="https://github.com/nyirog/gitlogfeed",
    project_urls={
        "Source": "https://github.com/nyirog/gitlogfeed",
        "Tracker": "https://github.com/nyirog/gitlogfeed/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
)

