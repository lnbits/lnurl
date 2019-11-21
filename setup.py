import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="lnurl",
    version="0.0.2",
    description="Simple implementation of LNURL for Python 3.5+",
    long_description=README,
    long_description_content_type="text/markdown",
    maintainer="jogco",
    maintainer_email="jogco@lnsms.world",
    url="https://github.com/jogco/lnurl",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
    ],
    packages=["lnurl"],
    include_package_data=True,
    install_requires=['bech32'],
)
