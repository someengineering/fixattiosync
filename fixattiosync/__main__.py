import sys
from .logger import add_args as logging_add_args, log
from .args import parse_args


def main() -> None:
    args = parse_args([logging_add_args])
    exit_code = 0
    log.info("Starting Fix Attio Sync")

    log.info("Shutdown complete")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
