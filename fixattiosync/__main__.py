import sys
from .logger import add_args as logging_add_args, log
from .args import parse_args
from .fixdata import FixData, add_args as fixdata_add_args
from .attiodata import AttioData, add_args as attio_add_args
from .sync import sync_fix_to_attio
from pprint import pprint


def main() -> None:
    args = parse_args([logging_add_args, attio_add_args, fixdata_add_args])
    if args.attio_api_key is None:
        log.error("Attio API key is required")
        sys.exit(1)
    if args.password is None:
        log.error("Database password is required")
        sys.exit(1)

    exit_code = 0
    log.info("Starting Fix Attio Sync")

    fix = FixData(db=args.db, user=args.user, password=args.password, host=args.host, port=args.port)
    fix.hydrate()

    attio = AttioData(args.attio_api_key)
    attio.hydrate()

    sync_fix_to_attio(fix, attio)

    log.info("Shutdown complete")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
