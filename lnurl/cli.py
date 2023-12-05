""" lnurl CLI """

import json
import sys

import click
import requests

from .core import encode as encode_lnurl
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
    decoded = handle_lnurl(lnurl)
    click.echo(decoded.json())


@click.command()
@click.argument("lnurl", type=str)
@click.argument("amount", type=int)
def payment_request(lnurl, amount):
    """
    make a payment_request
    """
    res = handle_lnurl(lnurl)
    decoded = res.dict()

    if decoded["tag"] and decoded["tag"] == "payRequest":
        if decoded["minSendable"] <= amount <= decoded["maxSendable"]:
            res = requests.get(decoded["callback"] + "?amount=" + str(amount))
            res.raise_for_status()
            return click.echo(json.dumps(res.json()))
        else:
            click.echo("Amount not in range.")
    else:
        click.echo("Not a payRequest:")
    click.echo(res.json())


def main():
    """main function"""
    command_group.add_command(encode)
    command_group.add_command(decode)
    command_group.add_command(handle)
    command_group.add_command(payment_request)
    command_group()


if __name__ == "__main__":
    main()
