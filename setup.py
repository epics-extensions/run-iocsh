# -*- coding: utf-8 -*-
from setuptools import setup

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

setup(
    name="run-iocsh",
    author="Benjamin Bertrand",
    author_email="benjamin.bertrand@esss.se",
    description="Wrapper to test iocsh",
    long_description=readme + "\n\n" + history,
    url="https://gitlab.esss.lu.se/ics-infrastructure/run-iocsh",
    license="BSD-2 license",
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    py_modules=["run_iocsh"],
    include_package_data=True,
    python_requires=">=3.6.0",
    keywords="iocsh",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD-2 License",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    entry_points={"console_scripts": ["run-iocsh=run_iocsh:main"]},
)
