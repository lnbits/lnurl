"""lnurl CLI"""

import asyncio
import sys

import click

from .core import encode as encode_lnurl
from .core import execute as execute_lnurl
from .core import handle as handle_lnurl
from .types import Lnurl

# disable tracebacks on exceptions
sys.tracebacklimit = 0


@click.group()
def command_group():
    """
    Python CLI for LNURL
    decode and encode lnurls"""


@click.command()
@click.argument("url", type=str)
def encode(url):
    """
    encode a URL
    """
    encoded = encode_lnurl(url)
    click.echo(encoded.bech32)


@click.command()
@click.argument("lnurl", type=str)
def decode(lnurl):
    """
    decode a LNURL
    """
    decoded = Lnurl(lnurl)
    click.echo(decoded.url)


@click.command()
@click.argument("lnurl", type=str)
def handle(lnurl):
    """
    handle a LNURL
    """
    decoded = asyncio.run(handle_lnurl(lnurl))
    click.echo(decoded.json())


@click.command()
@click.argument("lnurl", type=str)
@click.argument("msat_or_login", type=str, required=False)
def execute(lnurl, msat_or_login):
    """
    execute a LNURL request
    """
    if not msat_or_login:
        raise ValueError("You must provide either an amount_msat or a login_id.")
    res = asyncio.run(execute_lnurl(lnurl, msat_or_login))
    click.echo(res.json())


def main():
    """main function"""
    command_group.add_command(encode)
    command_group.add_command(decode)
    command_group.add_command(handle)
    command_group.add_command(execute)
    command_group()


if __name__ == "__main__":
    main()
