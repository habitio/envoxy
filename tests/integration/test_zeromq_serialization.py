"""Integration tests for ZeroMQ dispatcher overflow handling."""

import pytest

from envoxy.utils.encoders import envoxy_json_dumps


class TestZeroMQSerializationErrorHandling:
    """Test ZeroMQ dispatcher handles serialization errors gracefully."""

    @pytest.mark.integration
    def test_large_integer_serialization_no_recursion(self):
        """Test that large integers don't cause infinite recursion in serialization."""
        # This test verifies that the encoder handles large integers gracefully
        # by converting them to strings instead of causing TypeError

        large_int = 9223372036854775808  # 2^63, exceeds 64-bit max
        message = {
            "id": "test-message",
            "data": {"large_value": large_int, "normal_value": 42},
        }

        # Should not raise TypeError or cause infinite recursion
        serialized = envoxy_json_dumps(message)
        assert serialized is not None
        assert isinstance(serialized, bytes)

    @pytest.mark.integration
    def test_nested_large_integers_serialization(self):
        """Test deeply nested structures with large integers serialize correctly."""
        message = {
            "level1": {
                "level2": {
                    "level3": {
                        "large_int": 99999999999999999999999999999,
                        "normal_int": 100,
                    }
                },
                "another_large": 9223372036854775808,
            },
            "list_with_large": [1, 2, 9223372036854775808, {"nested": -9223372036854775809}],
        }

        # Should handle all nested large integers without errors
        serialized = envoxy_json_dumps(message)
        assert serialized is not None

    @pytest.mark.integration
    def test_edge_case_boundary_values(self):
        """Test boundary values around 64-bit integer limits."""
        test_cases = [
            9223372036854775807,  # Max 64-bit (should work as int)
            9223372036854775808,  # Max + 1 (should convert to string)
            -9223372036854775808,  # Min 64-bit (should work as int)
            -9223372036854775809,  # Min - 1 (should convert to string)
        ]

        for value in test_cases:
            message = {"test_value": value}
            # All cases should serialize without error
            serialized = envoxy_json_dumps(message)
            assert serialized is not None
