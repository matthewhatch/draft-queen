"""Unit tests for analytics service and endpoints."""

import os
os.environ["TESTING"] = "true"

import pytest
from decimal import Decimal

from backend.api.analytics_service import AnalyticsService


class TestAnalyticsServiceMathFunctions:
    """Test analytics service math/calculation functions."""

    def test_calculate_field_stats(self):
        """Test field statistics calculation."""
        values = [200.0, 205.0, 210.0, 215.0, 220.0, 225.0]
        stats = AnalyticsService._calculate_field_stats(values, "lbs")

        assert stats["unit"] == "lbs"
        assert stats["count"] == 6
        assert stats["min"] == 200.0
        assert stats["max"] == 225.0
        assert stats["average"] == 212.5
        assert stats["median"] == 212.5

    def test_calculate_field_stats_empty(self):
        """Test field statistics with empty list."""
        stats = AnalyticsService._calculate_field_stats([], "lbs")
        assert stats is None

    def test_calculate_field_stats_single_value(self):
        """Test field statistics with single value."""
        stats = AnalyticsService._calculate_field_stats([200.0], "lbs")

        assert stats["count"] == 1
        assert stats["min"] == 200.0
        assert stats["max"] == 200.0
        assert stats["average"] == 200.0
        assert stats["median"] == 200.0

    def test_calculate_field_stats_odd_count(self):
        """Test field statistics with odd number of values."""
        values = [100.0, 200.0, 300.0]
        stats = AnalyticsService._calculate_field_stats(values, "test")

        assert stats["count"] == 3
        assert stats["min"] == 100.0
        assert stats["max"] == 300.0
        assert stats["average"] == 200.0
        assert stats["median"] == 200.0

    def test_calculate_field_stats_even_count(self):
        """Test field statistics with even number of values."""
        values = [100.0, 200.0, 300.0, 400.0]
        stats = AnalyticsService._calculate_field_stats(values, "test")

        assert stats["count"] == 4
        assert stats["min"] == 100.0
        assert stats["max"] == 400.0
        assert stats["average"] == 250.0
        # Median of [100, 200, 300, 400] should be 250
        assert stats["median"] == 250.0

    def test_calculate_field_stats_percentiles_qb_height(self):
        """Test percentile calculations with QB height data."""
        # Realistic QB height data
        heights = [6.0, 6.1, 6.2, 6.3, 6.4]  # in feet
        stats = AnalyticsService._calculate_field_stats(heights, "feet")

        assert stats["count"] == 5
        assert stats["percentile_25"] == 6.1
        assert stats["median"] == 6.2
        assert stats["percentile_75"] == 6.3

    def test_percentile_calculation(self):
        """Test percentile calculation."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]

        # 25th percentile
        p25 = AnalyticsService._percentile(values, 25)
        assert 1.5 <= p25 <= 2.0

        # 50th percentile (median)
        p50 = AnalyticsService._percentile(values, 50)
        assert p50 == 3.0

        # 75th percentile
        p75 = AnalyticsService._percentile(values, 75)
        assert 3.5 <= p75 <= 4.5

    def test_percentile_with_empty_list(self):
        """Test percentile with empty list."""
        p = AnalyticsService._percentile([], 50)
        assert p == 0.0

    def test_percentile_p0(self):
        """Test percentile at p=0."""
        values = [10.0, 20.0, 30.0]
        p = AnalyticsService._percentile(values, 0)
        assert p == 10.0

    def test_percentile_p100(self):
        """Test percentile at p=100."""
        values = [10.0, 20.0, 30.0]
        p = AnalyticsService._percentile(values, 100)
        assert p == 30.0

    def test_percentile_single_value(self):
        """Test percentile with single value."""
        values = [42.0]
        p = AnalyticsService._percentile(values, 50)
        assert p == 42.0

    def test_percentile_interpolation(self):
        """Test percentile interpolation between values."""
        values = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

        # Test various percentiles
        p10 = AnalyticsService._percentile(values, 10)
        p50 = AnalyticsService._percentile(values, 50)
        p90 = AnalyticsService._percentile(values, 90)

        assert p10 == 10.0
        assert p50 == 50.0
        assert p90 == 90.0

    def test_field_stats_with_decimals(self):
        """Test field statistics with decimal values."""
        values = [Decimal("6.2"), Decimal("6.3"), Decimal("6.4")]
        # Convert to float for the function
        float_values = [float(v) for v in values]
        stats = AnalyticsService._calculate_field_stats(float_values, "feet")

        assert stats["count"] == 3
        assert stats["average"] == 6.3
        assert stats["median"] == 6.3

    def test_calculate_field_stats_rounding(self):
        """Test that field statistics round to 2 decimals."""
        values = [100.123, 200.456, 300.789]
        stats = AnalyticsService._calculate_field_stats(values, "test")

        # All values should be rounded to 2 decimals
        assert stats["min"] == 100.12
        assert stats["max"] == 300.79
        assert stats["average"] == 200.46
        assert isinstance(stats["median"], float)

    def test_calculate_field_stats_large_dataset(self):
        """Test field statistics with large dataset."""
        # Generate 1000 values
        values = [float(i) for i in range(1000)]
        stats = AnalyticsService._calculate_field_stats(values, "test")

        assert stats["count"] == 1000
        assert stats["min"] == 0.0
        assert stats["max"] == 999.0
        assert stats["average"] == 499.5
        assert stats["median"] == 499.5

    def test_calculate_field_stats_all_same_values(self):
        """Test field statistics when all values are the same."""
        values = [42.0] * 10
        stats = AnalyticsService._calculate_field_stats(values, "test")

        assert stats["count"] == 10
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["average"] == 42.0
        assert stats["median"] == 42.0
        assert stats["percentile_25"] == 42.0
        assert stats["percentile_75"] == 42.0

    def test_calculate_field_stats_negative_values(self):
        """Test field statistics with negative values."""
        values = [-10.0, -5.0, 0.0, 5.0, 10.0]
        stats = AnalyticsService._calculate_field_stats(values, "test")

        assert stats["min"] == -10.0
        assert stats["max"] == 10.0
        assert stats["average"] == 0.0
        assert stats["median"] == 0.0

    def test_percentile_with_two_values(self):
        """Test percentile with exactly two values."""
        values = [10.0, 20.0]

        p25 = AnalyticsService._percentile(values, 25)
        p50 = AnalyticsService._percentile(values, 50)
        p75 = AnalyticsService._percentile(values, 75)

        # With linear interpolation: 25th percentile should be between 10 and 20
        assert 10.0 <= p25 <= 15.0
        assert 12.5 <= p50 <= 17.5
        assert 15.0 <= p75 <= 20.0
