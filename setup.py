from setuptools import setup, find_packages

setup(
    name="datanexus",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "click",
    ],
    entry_points={
        "console_scripts": [
            "datanexus=src.cli.main:cli",
        ],
    },
)