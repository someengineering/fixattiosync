import re
import ipaddress


def valid_hostname(hostname: str) -> bool:
    pattern = r"^(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.[A-Za-z]{2,}$"
    return bool(re.match(pattern, hostname))


def valid_ip(ip_str: str) -> bool:
    try:
        ipaddress.ip_address(ip_str)
        return True
    except ValueError:
        return False


def valid_dbname(dbname: str) -> bool:
    pattern = r"^[A-Za-z0-9_-]{1,255}$"
    return bool(re.match(pattern, dbname))
