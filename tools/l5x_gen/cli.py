import argparse
from pathlib import Path

from .generator import generate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate L5X files from Jinja2 templates using a YAML config."
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="default.yaml",
        metavar="CONFIG",
        help="Path to the YAML config file (default: default.yaml)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        parser.error(f"Config file not found: {config_path}")

    print(f"Generating from {config_path}...")
    generate(config_path)
    print("Done.")


if __name__ == "__main__":
    main()
