import os
from argparse import ArgumentParser, Namespace
from typing import Callable, List


def parse_args(add_args: List[Callable[[ArgumentParser], None]]) -> Namespace:
    arg_parser = ArgumentParser(prog="fixattiosync", description="Attio Sync")

    for add_arg in add_args:
        add_arg(arg_parser)

    args = arg_parser.parse_args()

    return args
