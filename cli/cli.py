#!/usr/bin/env python3
"""RayAI CLI - Deploy agents and services with Ray Serve

Usage:
    rayai init <project_name> [--type=agent]
"""

import click
from commands import init


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """RayAI CLI - Deploy agents and services with Ray Serve"""
    pass


cli.add_command(init.init)


if __name__ == "__main__":
    cli()
