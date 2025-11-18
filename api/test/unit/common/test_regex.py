import re

import pytest

from clue.common.regex import (
    DOMAIN_ONLY_REGEX,
    DOMAIN_REGEX,
    EMAIL_PATH_REGEX,
    EMAIL_REGEX,
    HBS_AGENT_ID_ONLY_REGEX,
    HBS_AGENT_ID_REGEX,
    IP_ONLY_REGEX,
    IP_REGEX,
    IPV4_ONLY_REGEX,
    IPV4_REGEX,
    IPV6_ONLY_REGEX,
    IPV6_REGEX,
    MD5_REGEX,
    PORT_REGEX,
    SHA1_REGEX,
    SHA256_REGEX,
    URI_ONLY,
    URI_REGEX,
)


class TestDomainRegex:
    @pytest.mark.parametrize(
        "domain,expected",
        [
            ("example.com", True),
            ("subdomain.example.com", True),
            ("test.example.co.uk", True),
            ("a.b.c.d.example.com", True),
            ("xn--domain.com", True),
            ("test-domain.com", True),
            ("domain-with-hyphens.example.org", True),
            ("123domain.com", True),
            ("domain123.com", True),
            ("very-long-subdomain-name.example.com", True),
            # Partial test
            ("-domain.com", True),
            ("domain with spaces.com", True),
            ("domain_underscore.com", True),
            # Invalid cases
            ("domain.", False),
            ("", False),
            ("domain", False),
            (".com", False),
            ("domain-.com", False),
            ("domain..com", False),
            ("UPPERCASE.COM", False),  # Domain regex is lowercase only
        ],
    )
    def test_domain_regex(self, domain, expected):
        result = bool(re.search(DOMAIN_REGEX, domain))
        assert result == expected

    @pytest.mark.parametrize(
        "domain,expected",
        [
            ("example.com", True),
            ("subdomain.example.com", True),
            ("prefix-example.com-suffix", False),  # DOMAIN_ONLY should match entire string
            ("text before example.com", False),
            ("example.com text after", False),
            ("domain with spaces.com", False),
            ("domain_underscore.com", False),
            ("-domain.com", False),
        ],
    )
    def test_domain_only_regex(self, domain, expected):
        result = bool(re.match(DOMAIN_ONLY_REGEX, domain))
        assert result == expected


class TestEmailRegex:
    @pytest.mark.parametrize(
        "email,expected",
        [
            ("user@example.com", True),
            ("test.email@domain.co.uk", True),
            ("user+tag@example.org", True),
            ("user_name@example.com", True),
            ("user-name@example.com", True),
            ("123user@example.com", True),
            ("user123@example.com", True),
            ("user@subdomain.example.com", True),
            ("valid.email+tag@very-long-domain.example.org", True),
            # Invalid cases
            ("", False),
            ("user", False),
            ("@example.com", False),
            ("user@", False),
            ("user@domain", False),
            ("user name@example.com", False),
            ("user..name@example.com", False),
            ("user@domain..com", False),
            (".user@example.com", False),
            ("user.@example.com", False),
        ],
    )
    def test_email_regex(self, email, expected):
        result = bool(re.match(EMAIL_REGEX, email))
        assert result == expected


class TestIPv4Regex:
    @pytest.mark.parametrize(
        "ip,expected",
        [
            ("192.168.1.1", True),
            ("10.0.0.1", True),
            ("172.16.254.1", True),
            ("127.0.0.1", True),
            ("0.0.0.0", True),
            ("255.255.255.255", True),
            ("8.8.8.8", True),
            ("1.2.3.4", True),
            # Partial Cases
            ("192.168.1.1.1", True),
            ("192.168.1.256", True),
            # Invalid cases
            ("", False),
            ("192.168.1", False),
            ("192.168.1.-1", False),
            ("192.168.01.1", True),  # Leading zeros are allowed in the regex
            ("192.168.1.001", True),
            ("text.text.text.text", False),
            ("192.168.1.a", False),
        ],
    )
    def test_ipv4_regex(self, ip, expected):
        result = bool(re.search(IPV4_REGEX, ip))
        assert result == expected

    @pytest.mark.parametrize(
        "ip,expected",
        [
            ("192.168.1.1", True),
            ("prefix-192.168.1.1-suffix", False),  # IPV4_ONLY should match entire string
            ("192.168.1.1.1", False),
            ("text 192.168.1.1", False),
            ("192.168.1.1 text", False),
            ("192.168.1.256", False),
        ],
    )
    def test_ipv4_only_regex(self, ip, expected):
        result = bool(re.match(IPV4_ONLY_REGEX, ip))
        assert result == expected


class TestIPv6Regex:
    @pytest.mark.parametrize(
        "ip,expected",
        [
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", True),
            ("2001:db8:85a3:0:0:8a2e:370:7334", True),
            ("2001:db8:85a3::8a2e:370:7334", True),
            ("::1", True),
            ("::", True),
            ("2001:db8::1", True),
            ("::ffff:192.168.1.1", True),  # IPv4-mapped IPv6
            ("2001:db8:85a3::8a2e:370:192.168.1.1", True),  # IPv4-embedded IPv6
            ("fe80::1%lo0", True),  # Link-local with zone ID
            ("fe80::1%eth0", True),
            # Partial cases
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334:extra", True),
            ("2001:0db8:85a3::8a2e::7334", True),  # Multiple ::
            ("gggg::1", True),  # Invalid hex
            ("2001:0db8:85a3:0000:0000:8a2e:0370:733g", True),  # Invalid hex
            # Invalid cases
            ("", False),
        ],
    )
    def test_ipv6_regex(self, ip, expected):
        result = bool(re.search(IPV6_REGEX, ip))
        assert result == expected

    @pytest.mark.parametrize(
        "ip,expected",
        [
            ("2001:db8::1", True),
            ("prefix-2001:db8::1-suffix", False),  # IPV6_ONLY should match entire string
            ("text 2001:db8::1", False),
            ("2001:db8::1 text", False),
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334:extra", False),
            ("2001:0db8:85a3::8a2e::7334", False),  # Multiple ::
            ("gggg::1", False),  # Invalid hex
            ("2001:0db8:85a3:0000:0000:8a2e:0370:733g", False),  # Invalid hex
        ],
    )
    def test_ipv6_only_regex(self, ip, expected):
        result = bool(re.match(IPV6_ONLY_REGEX, ip))
        assert result == expected


class TestIPRegex:
    @pytest.mark.parametrize(
        "ip,expected",
        [
            # ipv4
            ("192.168.1.1", True),
            ("10.0.0.1", True),
            ("172.16.254.1", True),
            ("127.0.0.1", True),
            ("0.0.0.0", True),
            ("255.255.255.255", True),
            ("8.8.8.8", True),
            ("1.2.3.4", True),
            # Partial Cases
            ("192.168.1.1.1", True),
            ("192.168.1.256", True),
            # Invalid cases
            ("", False),
            ("192.168.1", False),
            ("192.168.1.-1", False),
            ("192.168.01.1", True),  # Leading zeros are allowed in the regex
            ("192.168.1.001", True),
            ("text.text.text.text", False),
            ("192.168.1.a", False),
            # ipv6
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", True),
            ("2001:db8:85a3:0:0:8a2e:370:7334", True),
            ("2001:db8:85a3::8a2e:370:7334", True),
            ("::1", True),
            ("::", True),
            ("2001:db8::1", True),
            ("::ffff:192.168.1.1", True),  # IPv4-mapped IPv6
            ("2001:db8:85a3::8a2e:370:192.168.1.1", True),  # IPv4-embedded IPv6
            ("fe80::1%lo0", True),  # Link-local with zone ID
            ("fe80::1%eth0", True),
            # Partial cases
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334:extra", True),
            ("2001:0db8:85a3::8a2e::7334", True),  # Multiple ::
            ("gggg::1", True),  # Invalid hex
            ("2001:0db8:85a3:0000:0000:8a2e:0370:733g", True),  # Invalid hex
            # Invalid cases
            ("", False),
        ],
    )
    def test_ip_regex(self, ip, expected):
        result = bool(re.search(IP_REGEX, ip))
        assert result == expected

    @pytest.mark.parametrize(
        "ip,expected",
        [
            # ipv4
            ("192.168.1.1", True),
            ("prefix-192.168.1.1-suffix", False),  # IPV4_ONLY should match entire string
            ("192.168.1.1.1", False),
            ("text 192.168.1.1", False),
            ("192.168.1.1 text", False),
            ("192.168.1.256", False),
            # ipv6
            ("2001:db8::1", True),
            ("prefix-2001:db8::1-suffix", False),  # IPV6_ONLY should match entire string
            ("text 2001:db8::1", False),
            ("2001:db8::1 text", False),
            ("2001:0db8:85a3:0000:0000:8a2e:0370:7334:extra", False),
            ("2001:0db8:85a3::8a2e::7334", False),  # Multiple ::
            ("gggg::1", False),  # Invalid hex
            ("2001:0db8:85a3:0000:0000:8a2e:0370:733g", False),  # Invalid hex
        ],
    )
    def test_ip_only_regex(self, ip, expected):
        result = bool(re.match(IP_ONLY_REGEX, ip))
        assert result == expected


class TestPortRegex:
    @pytest.mark.parametrize(
        "port,expected",
        [
            ("0", True),
            ("1", True),
            ("80", True),
            ("443", True),
            ("8080", True),
            ("65535", True),  # Maximum valid port
            ("22", True),
            ("3389", True),
            # Invalid cases
            ("", False),
            ("-1", False),
            ("65536", False),  # Above maximum
            ("99999", False),
            ("01", False),  # Leading zero not allowed (except for 0)
            ("port", False),
            ("80.5", False),
            (" 80", False),
            ("80 ", False),
        ],
    )
    def test_port_regex(self, port, expected):
        result = bool(re.match(PORT_REGEX, port))
        assert result == expected


class TestHashRegex:
    @pytest.mark.parametrize(
        "hash_value,expected",
        [
            ("d41d8cd98f00b204e9800998ecf8427e", True),  # MD5 of empty string
            ("5d41402abc4b2a76b9719d911017c592", True),
            ("098f6bcd4621d373cade4e832627b4f6", True),
            ("DEADBEEFDEADBEEFDEADBEEFDEADBEEF", True),  # Uppercase
            ("deadbeefdeadbeefdeadbeefdeadbeef", True),  # Lowercase
            # Invalid cases
            ("", False),
            ("d41d8cd98f00b204e9800998ecf8427", False),  # Too short
            ("d41d8cd98f00b204e9800998ecf8427e1", False),  # Too long
            ("d41d8cd98f00b204e9800998ecf8427g", False),  # Invalid hex
            ("d41d8cd9-8f00-b204-e980-0998ecf8427e", False),  # With dashes
        ],
    )
    def test_md5_regex(self, hash_value, expected):
        result = bool(re.match(MD5_REGEX, hash_value))
        assert result == expected

    @pytest.mark.parametrize(
        "hash_value,expected",
        [
            ("adc83b19e793491b1c6ea0fd8b46cd9f32e592fc", True),  # SHA1 of empty string
            ("356a192b7913b04c54574d18c28d46e6395428ab", True),
            ("da39a3ee5e6b4b0d3255bfef95601890afd80709", True),
            ("DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF", True),  # Uppercase
            ("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef", True),  # Lowercase
            # Invalid cases
            ("", False),
            ("adc83b19e793491b1c6ea0fd8b46cd9f32e592f", False),  # Too short
            ("adc83b19e793491b1c6ea0fd8b46cd9f32e592fc1", False),  # Too long
            ("adc83b19e793491b1c6ea0fd8b46cd9f32e592fg", False),  # Invalid hex
        ],
    )
    def test_sha1_regex(self, hash_value, expected):
        result = bool(re.match(SHA1_REGEX, hash_value))
        assert result == expected

    @pytest.mark.parametrize(
        "hash_value,expected",
        [
            ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", True),  # SHA256 of empty string
            ("2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae", True),
            ("deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef", True),  # Lowercase
            ("DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF", True),  # Uppercase
            # Invalid cases
            ("", False),
            ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b85", False),  # Too short
            ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b8551", False),  # Too long
            ("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b85g", False),  # Invalid hex
        ],
    )
    def test_sha256_regex(self, hash_value, expected):
        result = bool(re.match(SHA256_REGEX, hash_value))
        assert result == expected


class TestURIRegex:
    @pytest.mark.parametrize(
        "uri,expected",
        [
            ("http://example.com", True),
            ("https://example.com", True),
            ("https://www.example.com/path", True),
            ("https://subdomain.example.com:8080/path?query=value", True),
            ("ftp://files.example.com/file.txt", True),
            ("http://192.168.1.1", True),
            ("https://192.168.1.1:8080/path", True),
            ("http://[2001:db8::1]/path", True),  # IPv6 in brackets
            ("https://user@example.com/path", True),
            ("http://user:pass@example.com/path", True),
            ("https://example.com:443", True),
            ("example.com:443", True),
            ("example.com", True),
            # Partial Cases
            ("://example.com", True),  # Missing scheme name
            ("http:example.com", True),  # Missing //
            # Invalid cases
            ("", False),
            ("http://", False),  # Missing host
            ("http://example", False),  # Domain regex requires TLD
        ],
    )
    def test_uri_regex(self, uri, expected):
        result = bool(re.search(URI_REGEX, uri))
        assert result == expected

    @pytest.mark.parametrize(
        "uri,expected",
        [
            ("http://example.com", True),
            ("https://example.com/path", True),
            ("prefix http://example.com suffix", False),  # URI_ONLY should match entire string
            ("text before http://example.com", False),
            ("://example.com", False),  # Missing scheme name
            ("http:example.com", False),  # Missing //
        ],
    )
    def test_uri_only_regex(self, uri, expected):
        result = bool(re.match(URI_ONLY, uri))
        assert result == expected


class TestEmailPathRegex:
    @pytest.mark.parametrize(
        "path,expected",
        [
            ("SMTP_EMAIL://user@example.com", True),
            ("IMAP_EMAIL://user@example.com", True),
            ("ABC_EMAIL://path/to/email", True),
            # Invalid cases
            ("", False),
            ("EMAIL://user@example.com", False),
            ("_EMAIL://user@example.com", False),
            ("POP3_EMAIL://user@example.com", False),
            ("email://user@example.com", False),  # Lowercase
            ("SMTP_EMAIL", False),  # Missing ://
            ("SMTP://user@example.com", False),  # Missing _EMAIL
            ("SMTP_EMAIL:/user@example.com", False),  # Missing second /
        ],
    )
    def test_email_path_regex(self, path, expected):
        result = bool(re.match(EMAIL_PATH_REGEX, path))
        assert result == expected


class TestHBSAgentIDRegex:
    @pytest.mark.parametrize(
        "agent_id,expected",
        [
            ("1234.5678.9abc.def0", True),
            ("a.b.c.d", True),
            ("1.2.3.4", True),
            ("A.B.C.D", True),  # Uppercase
            ("123.456.789.abc", True),
            ("f.e.d.c", True),
            # Partial Cases
            ("1234.5678.9abc.def0.extra", True),  # Extra segment
            ("12345.5678.9abc.def0", True),  # Segment too long
            ("1234.5678.9abc.def0g", True),  # Invalid hex in last segment
            ("1234.5678.9abc.defg", True),  # Invalid hex
            # Invalid cases
            ("", False),
            ("abcd.efgh.1234.5678", False),
            ("1234.5678.9abc", False),  # Missing segment
            ("1234..9abc.def0", False),  # Empty segment
        ],
    )
    def test_hbs_agent_id_regex(self, agent_id, expected):
        result = bool(re.search(HBS_AGENT_ID_REGEX, agent_id))
        assert result == expected

    @pytest.mark.parametrize(
        "agent_id,expected",
        [
            ("1234.5678.9abc.def0", True),
            ("a.b.c.d", True),
            ("1.2.3.4", True),
            # Partial Cases
            ("1234.5678.9abc.def0.extra", False),  # Extra segment
            ("12345.5678.9abc.def0", False),  # Segment too long
            ("1234.5678.9abc.def0g", False),  # Invalid hex in last segment
            ("1234.5678.9abc.defg", False),  # Invalid hex
            # Invalid cases
            ("", False),
            ("1234.5678.9abc", False),  # Missing segment
            ("12345.5678.9abc.def0", False),  # Segment too long
            ("1234..9abc.def0", False),  # Empty segment
            ("1234.5678.9abc.def0g", False),  # Invalid hex in last segment
            ("1234.5678.9abc.defg", False),  # Invalid hex
            ("abcd.efgh.1234.5678", False),
        ],
    )
    def test_hbs_agent_id_only_regex(self, agent_id, expected):
        result = bool(re.search(HBS_AGENT_ID_ONLY_REGEX, agent_id))
        assert result == expected
