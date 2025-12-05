"""Unit tests for JSON encoders."""

import datetime
import decimal

import orjson
import pytest

from envoxy.utils.encoders import (
    EnvoxyJsonEncoder,
    envoxy_json_dumps,
    envoxy_json_encode_default,
    envoxy_json_loads,
)


class TestEnvoxyJsonEncoder:
    """Test cases for the legacy JSON encoder."""

    def test_decimal_encoding(self):
        """Test that Decimal values are encoded as floats."""
        encoder = EnvoxyJsonEncoder()
        result = encoder.default(decimal.Decimal("123.45"))
        assert result == 123.45
        assert isinstance(result, float)

    def test_datetime_encoding(self):
        """Test that datetime values are encoded as ISO format strings."""
        encoder = EnvoxyJsonEncoder()
        dt = datetime.datetime(2025, 12, 5, 10, 30, 45)
        result = encoder.default(dt)
        assert result == "2025-12-05T10:30:45"

    def test_date_encoding(self):
        """Test that date values are encoded as ISO format strings."""
        encoder = EnvoxyJsonEncoder()
        d = datetime.date(2025, 12, 5)
        result = encoder.default(d)
        assert result == "2025-12-05"


class TestEnvoxyJsonEncodeDefault:
    """Test cases for the orjson default encoder function."""

    def test_decimal_encoding(self):
        """Test that Decimal values are encoded as floats."""
        result = envoxy_json_encode_default(decimal.Decimal("123.45"))
        assert result == 123.45
        assert isinstance(result, float)

    def test_datetime_encoding(self):
        """Test that datetime values are encoded as ISO format strings."""
        dt = datetime.datetime(2025, 12, 5, 10, 30, 45)
        result = envoxy_json_encode_default(dt)
        assert result == "2025-12-05T10:30:45"

    def test_date_encoding(self):
        """Test that date values are encoded as ISO format strings."""
        d = datetime.date(2025, 12, 5)
        result = envoxy_json_encode_default(d)
        assert result == "2025-12-05"

    def test_unsupported_type_raises_error(self):
        """Test that unsupported types raise TypeError."""
        with pytest.raises(TypeError):
            envoxy_json_encode_default(set([1, 2, 3]))

    @pytest.mark.unit
    def test_int64_max_value(self):
        """Test that maximum 64-bit integer is handled correctly."""
        max_64bit = 9223372036854775807  # 2^63 - 1
        result = envoxy_json_dumps({"value": max_64bit})
        decoded = envoxy_json_loads(result)
        assert decoded["value"] == max_64bit

    @pytest.mark.unit
    def test_int64_min_value(self):
        """Test that minimum 64-bit integer is handled correctly."""
        min_64bit = -9223372036854775808  # -2^63
        result = envoxy_json_dumps({"value": min_64bit})
        decoded = envoxy_json_loads(result)
        assert decoded["value"] == min_64bit

    @pytest.mark.unit
    def test_large_positive_integer_converted_to_string(self):
        """Test that integers exceeding 64-bit range are converted to strings."""
        large_int = 18446744073709551616  # 2^64 (exceeds unsigned max)
        result = envoxy_json_dumps({"value": large_int})
        decoded = envoxy_json_loads(result)
        # Should be converted to string
        assert decoded["value"] == str(large_int)
        assert isinstance(decoded["value"], str)

    @pytest.mark.unit
    def test_large_negative_integer_converted_to_string(self):
        """Test that large negative integers exceeding 64-bit range are converted to strings."""
        large_negative = -9223372036854775809  # -2^63 - 1 (exceeds min)
        result = envoxy_json_dumps({"value": large_negative})
        decoded = envoxy_json_loads(result)
        # Should be converted to string
        assert decoded["value"] == str(large_negative)
        assert isinstance(decoded["value"], str)

    @pytest.mark.unit
    def test_very_large_integer_converted_to_string(self):
        """Test that very large integers are converted to strings."""
        very_large = 99999999999999999999999999999
        result = envoxy_json_dumps({"value": very_large})
        decoded = envoxy_json_loads(result)
        assert decoded["value"] == str(very_large)
        assert isinstance(decoded["value"], str)

    @pytest.mark.unit
    def test_nested_large_integers(self):
        """Test that large integers in nested structures are handled."""
        data = {
            "normal": 42,
            "large": 18446744073709551616,  # 2^64
            "nested": {"very_large": 99999999999999999999999999999, "normal": 100},
            "list": [1, 18446744073709551616, {"key": -9223372036854775809}],
        }
        result = envoxy_json_dumps(data)
        decoded = envoxy_json_loads(result)

        assert decoded["normal"] == 42
        assert decoded["large"] == "18446744073709551616"
        assert decoded["nested"]["very_large"] == "99999999999999999999999999999"
        assert decoded["nested"]["normal"] == 100
        assert decoded["list"][0] == 1
        assert decoded["list"][1] == "18446744073709551616"
        assert decoded["list"][2]["key"] == "-9223372036854775809"

    @pytest.mark.unit
    def test_mixed_types_with_large_integers(self):
        """Test encoding of mixed types including large integers."""
        data = {
            "int": 42,
            "large_int": 18446744073709551616,  # 2^64
            "float": 3.14,
            "decimal": decimal.Decimal("123.45"),
            "datetime": datetime.datetime(2025, 12, 5, 10, 30, 45),
            "date": datetime.date(2025, 12, 5),
            "string": "test",
            "bool": True,
            "null": None,
        }
        result = envoxy_json_dumps(data)
        decoded = envoxy_json_loads(result)

        assert decoded["int"] == 42
        assert decoded["large_int"] == "18446744073709551616"
        assert decoded["float"] == 3.14
        assert decoded["decimal"] == 123.45
        assert decoded["datetime"] == "2025-12-05T10:30:45"
        assert decoded["date"] == "2025-12-05"
        assert decoded["string"] == "test"
        assert decoded["bool"] is True
        assert decoded["null"] is None


class TestEnvoxyJsonDumpsLoads:
    """Test cases for envoxy_json_dumps and envoxy_json_loads."""

    @pytest.mark.unit
    def test_round_trip_simple_data(self):
        """Test encoding and decoding simple data structures."""
        data = {"name": "test", "value": 42, "active": True}
        encoded = envoxy_json_dumps(data)
        decoded = envoxy_json_loads(encoded)
        assert decoded == data

    @pytest.mark.unit
    def test_round_trip_with_datetime(self):
        """Test encoding and decoding with datetime objects."""
        dt = datetime.datetime(2025, 12, 5, 10, 30, 45)
        data = {"timestamp": dt}
        encoded = envoxy_json_dumps(data)
        decoded = envoxy_json_loads(encoded)
        assert decoded["timestamp"] == "2025-12-05T10:30:45"

    @pytest.mark.unit
    def test_bytes_output(self):
        """Test that envoxy_json_dumps returns bytes."""
        result = envoxy_json_dumps({"test": "value"})
        assert isinstance(result, bytes)
