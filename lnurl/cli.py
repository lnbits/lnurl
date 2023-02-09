""" lnurl CLI """
import sys
import click

from .types import Lnurl
from .core import handle as handle_lnurl
from .core import encode as encode_lnurl

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
    decoded = handle_lnurl(lnurl)
    print(decoded)
    click.echo(decoded)


def main():
    """main function"""
    command_group.add_command(encode)
    command_group.add_command(decode)
    command_group.add_command(handle)
    command_group()


if __name__ == "__main__":
    main()
