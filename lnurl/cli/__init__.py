import click


@click.command()
@click.option("--config", help="Configuration file path", required=True)
# Can't figure out how to detect if this option was present, so keeping it
# commented to not confuse the users
#@click.option("--private-channels", "channel_type", help="Request accepted channels to be private", flag_value = 1)
#@click.option("--public-channels", "channel_type", help="Request accepted channels to be public. This is the default.", flag_value = 0)
def decode(config: str):
    """Entry point - the lnurl command"""
    print("hello, world!")

