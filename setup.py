from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bitcoinrpc",
    version="0.1.0",
    author="Julian",
    author_email="your.email@example.com",
    description="A Python Bitcoin RPC client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Julian128/bitcoinrpc",
    packages=find_packages(),
    classifiers=[
    ],
    python_requires=">=3.7",
    install_requires=[
    ],
)