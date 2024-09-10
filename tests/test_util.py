from fixattiosync.utils import valid_hostname, valid_ip


def test_valid_hostname():
    # Positive tests
    assert valid_hostname("some.engineering") is True
    assert valid_hostname("example.com") is True
    assert valid_hostname("sub.example.com") is True
    assert valid_hostname("subdomain.example-domain.com") is True
    assert valid_hostname("a.com") is True

    # Negative tests
    assert valid_hostname("-example.com") is False
    assert valid_hostname("example-.com") is False
    assert valid_hostname("example..com") is False
    assert valid_hostname("example.c") is False
    assert valid_hostname("example_1.com") is False

    # Edge cases
    assert valid_hostname("example") is False
    assert valid_hostname(".com") is False


def test_valid_ip():
    assert valid_ip("192.168.1.1")  # Valid IPv4
    assert valid_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")  # Valid IPv6
    assert not valid_ip("256.256.256.256")  # Invalid IPv4
    assert not valid_ip("2001:0db8:85a3:0000:0000:8a2e:0370:GZ11")  # Invalid IPv6
    assert not valid_ip("random_string")  # Not an IP
