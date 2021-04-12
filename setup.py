from os import path
from setuptools import setup, find_packages


with open(path.join(path.abspath(path.dirname(__file__)), "README.md")) as f:
    long_description = f.read()


setup(
    name="lnurl",
    version="0.3.6",
    url="https://github.com/lnbits/lnurl",
    author="jogco",
    author_email="jogco@lnsms.world",
    maintainer="eillarra",
    maintainer_email="eneko@illarra.com",
    license="MIT",
    description="LNURL implementation for Python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="bitcoin lightning-network lnurl",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Utilities",
    ],
    packages=find_packages(exclude=["tests"]),
    python_requires=">=3.6",
    install_requires=["bech32", "pydantic", "typing-extensions; python_version<'3.8'"],
    extras_require={ "cli": ["click", "toml", "requests"] },
    entry_points={
        "console_scripts": [ "lnurl = lnurl.cli:lnurl [cli]" ],
        "lnurl.rpc_handlers": [ "lnd_rest = lnurl.cli.lnrpc.lnd_rest:LndRestRPC [cli]" ]
    },
    zip_safe=False,
)
