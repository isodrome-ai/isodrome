import argparse

from isodrome import __version__


def main() -> None:
    parser = argparse.ArgumentParser(prog="iso", description="Isodrome CLI")
    parser.add_argument("--version", action="version", version=f"isodrome {__version__}")
    parser.parse_args()
    print(f"isodrome {__version__}: early development. See https://isodrome.ai")
