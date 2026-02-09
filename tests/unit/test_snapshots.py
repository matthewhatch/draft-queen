"""Unit tests for snapshot manager."""

import pytest
import json
import gzip
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from data_pipeline.snapshots.snapshot_manager import (
    SnapshotManager,
    ProspectSnapshot,
    SnapshotMetadata,
)


@pytest.fixture
def temp_snapshot_dir():
    """Create temporary directory for snapshots."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def snapshot_manager(temp_snapshot_dir):
    """Create snapshot manager with temporary directories."""
    archive_dir = Path(temp_snapshot_dir) / "archive"
    snapshot_dir = Path(temp_snapshot_dir) / "snapshots"

    return SnapshotManager(
        snapshot_dir=str(snapshot_dir),
        archive_dir=str(archive_dir),
        archive_after_days=3,
    )


@pytest.fixture
def sample_prospect_records():
    """Create sample prospect records."""
    return [
        {
            "prospect_id": "P001",
            "name": "Patrick Mahomes",
            "position": "QB",
            "college": "Texas Tech",
            "height": 6.2,
            "weight": 220,
            "forty_time": 4.8,
        },
        {
            "prospect_id": "P002",
            "name": "Travis Kelce",
            "position": "TE",
            "college": "Cincinnati",
            "height": 6.4,
            "weight": 260,
            "forty_time": 4.6,
        },
        {
            "prospect_id": "P003",
            "name": "Joe Burrow",
            "position": "QB",
            "college": "LSU",
            "height": 6.3,
            "weight": 221,
            "forty_time": 4.79,
        },
    ]


class TestSnapshotManagerBasic:
    """Test basic snapshot manager functionality."""

    def test_manager_initialization(self, snapshot_manager):
        """Test manager initializes correctly."""
        assert snapshot_manager is not None
        assert snapshot_manager.snapshot_dir.exists()
        assert snapshot_manager.archive_dir.exists()
        assert snapshot_manager.archive_after_days == 3

    def test_create_snapshot(self, snapshot_manager, sample_prospect_records):
        """Test creating a snapshot."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        assert metadata is not None
        assert metadata.snapshot_id == f"snapshot_{snapshot_date.strftime('%Y%m%d')}"
        assert metadata.total_records == 3
        assert metadata.uncompressed_size_bytes > 0

    def test_snapshot_file_created(self, snapshot_manager, sample_prospect_records):
        """Test snapshot file is created on disk."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        snapshot_file = snapshot_manager.snapshot_dir / f"{metadata.snapshot_id}.json"
        assert snapshot_file.exists()

    def test_snapshot_data_valid_json(self, snapshot_manager, sample_prospect_records):
        """Test snapshot file contains valid JSON."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        snapshot_file = snapshot_manager.snapshot_dir / f"{metadata.snapshot_id}.json"
        data = json.loads(snapshot_file.read_text())

        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["prospect_id"] == "P001"


class TestSnapshotMetadata:
    """Test snapshot metadata."""

    def test_metadata_creation(self):
        """Test creating snapshot metadata."""
        date = datetime.utcnow()
        metadata = SnapshotMetadata(
            snapshot_id="snapshot_20260210",
            snapshot_date=date,
            total_records=100,
        )

        assert metadata.snapshot_id == "snapshot_20260210"
        assert metadata.total_records == 100
        assert not metadata.archived

    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        date = datetime.utcnow()
        metadata = SnapshotMetadata(
            snapshot_id="snapshot_20260210",
            snapshot_date=date,
            total_records=100,
        )

        metadata_dict = metadata.as_dict()

        assert metadata_dict["snapshot_id"] == "snapshot_20260210"
        assert metadata_dict["total_records"] == 100
        assert "snapshot_date" in metadata_dict


class TestProspectSnapshot:
    """Test prospect snapshot record."""

    def test_prospect_snapshot_creation(self):
        """Test creating prospect snapshot."""
        date = datetime.utcnow()
        data = {"name": "John Doe", "position": "QB"}

        ps = ProspectSnapshot(
            prospect_id="P001",
            snapshot_date=date,
            data=data,
        )

        assert ps.prospect_id == "P001"
        assert ps.data["name"] == "John Doe"
        assert not ps.changed_from_previous

    def test_prospect_snapshot_hash(self):
        """Test hash calculation for prospect data."""
        ps = ProspectSnapshot(
            prospect_id="P001",
            snapshot_date=datetime.utcnow(),
            data={"name": "John Doe", "position": "QB"},
        )

        hash1 = ps.calculate_hash()
        assert hash1 is not None
        assert len(hash1) == 64  # SHA256 hex digest length

        # Same data should produce same hash
        hash2 = ps.calculate_hash()
        assert hash1 == hash2

    def test_prospect_snapshot_hash_changes(self):
        """Test hash changes with data changes."""
        ps = ProspectSnapshot(
            prospect_id="P001",
            snapshot_date=datetime.utcnow(),
            data={"name": "John Doe", "position": "QB"},
        )

        hash1 = ps.calculate_hash()

        # Change data
        ps.data["position"] = "RB"
        hash2 = ps.calculate_hash()

        assert hash1 != hash2


class TestSnapshotCompression:
    """Test snapshot compression."""

    def test_compress_snapshot(self, snapshot_manager, sample_prospect_records):
        """Test compressing a snapshot."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        success = snapshot_manager.compress_snapshot(metadata.snapshot_id)
        assert success

        # Check compressed file exists
        compressed_file = snapshot_manager.snapshot_dir / f"{metadata.snapshot_id}.json.gz"
        assert compressed_file.exists()

        # Check uncompressed file is removed
        uncompressed_file = snapshot_manager.snapshot_dir / f"{metadata.snapshot_id}.json"
        assert not uncompressed_file.exists()

    def test_compressed_snapshot_readable(self, snapshot_manager, sample_prospect_records):
        """Test compressed snapshot can be read."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        snapshot_manager.compress_snapshot(metadata.snapshot_id)

        # Try to read compressed file
        compressed_file = snapshot_manager.snapshot_dir / f"{metadata.snapshot_id}.json.gz"
        with gzip.open(compressed_file, "rt") as f:
            data = json.load(f)

        assert len(data) == 3
        assert data[0]["prospect_id"] == "P001"

    def test_compression_reduces_size(self, snapshot_manager, sample_prospect_records):
        """Test compression actually reduces file size."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)
        original_size = metadata.uncompressed_size_bytes

        snapshot_manager.compress_snapshot(metadata.snapshot_id)

        assert metadata.compressed_size_bytes < original_size


class TestSnapshotArchival:
    """Test snapshot archival functionality."""

    def test_archive_snapshot(self, snapshot_manager, sample_prospect_records):
        """Test archiving a snapshot."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        # First compress
        snapshot_manager.compress_snapshot(metadata.snapshot_id)

        # Then archive
        success = snapshot_manager.archive_snapshot(
            metadata.snapshot_id,
            "s3://prospect-snapshots/test.json.gz",
        )
        assert success

        # Check metadata updated
        assert metadata.archived

    def test_restore_snapshot(self, snapshot_manager, sample_prospect_records):
        """Test restoring an archived snapshot."""
        snapshot_date = datetime.utcnow()

        metadata = snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        # Archive
        snapshot_manager.compress_snapshot(metadata.snapshot_id)
        snapshot_manager.archive_snapshot(
            metadata.snapshot_id,
            "s3://prospect-snapshots/test.json.gz",
        )

        # Check archived
        assert metadata.archived

        # Restore
        success = snapshot_manager.restore_snapshot(metadata.snapshot_id)
        assert success

        # Check restored
        assert not metadata.archived


class TestHistoricalQueries:
    """Test historical data queries."""

    def test_get_historical_data(self, snapshot_manager, sample_prospect_records):
        """Test retrieving historical data."""
        snapshot_date = datetime(2026, 2, 10)

        snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        # Query historical data
        data = snapshot_manager.get_historical_data("P001", snapshot_date)

        assert data is not None
        assert data["prospect_id"] == "P001"
        assert data["name"] == "Patrick Mahomes"

    def test_get_historical_data_nonexistent(self, snapshot_manager):
        """Test querying nonexistent prospect."""
        snapshot_date = datetime(2026, 2, 10)

        # No snapshots exist
        data = snapshot_manager.get_historical_data("P999", snapshot_date)

        assert data is None

    def test_get_data_as_of_date(self, snapshot_manager, sample_prospect_records):
        """Test getting all data as of a specific date."""
        snapshot_date = datetime(2026, 2, 10)

        snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        all_data = snapshot_manager.get_data_as_of_date(snapshot_date)

        assert len(all_data) == 3
        assert all_data[0]["prospect_id"] == "P001"

    def test_get_prospect_history(self, snapshot_manager, sample_prospect_records):
        """Test getting prospect history over time."""
        # Create snapshots for multiple days
        import copy
        base_date = datetime(2026, 2, 10)

        for i in range(3):
            current_date = base_date + timedelta(days=i)
            records = copy.deepcopy(sample_prospect_records)

            # Modify one record to track changes
            records[0]["forty_time"] = 4.8 - (i * 0.05)

            snapshot_manager.create_snapshot(records, current_date)

        # Get history
        history = snapshot_manager.get_prospect_history("P001", base_date, base_date + timedelta(days=2))

        assert len(history) == 3
        assert history[0][1]["forty_time"] == pytest.approx(4.8, abs=0.01)
        assert history[1][1]["forty_time"] == pytest.approx(4.75, abs=0.01)
        assert history[2][1]["forty_time"] == pytest.approx(4.7, abs=0.01)


class TestSnapshotCleanup:
    """Test cleanup and archival of old snapshots."""

    def test_cleanup_old_snapshots(self, snapshot_manager, sample_prospect_records):
        """Test cleaning up old snapshots."""
        # Create old snapshot
        old_date = datetime.utcnow() - timedelta(days=5)
        snapshot_manager.create_snapshot(sample_prospect_records, old_date)

        # Compress it first
        snapshot_id = f"snapshot_{old_date.strftime('%Y%m%d')}"
        snapshot_manager.compress_snapshot(snapshot_id)

        # Cleanup (archive_after_days = 3)
        archived_count = snapshot_manager.cleanup_old_snapshots()

        assert archived_count == 1

        # Check metadata
        metadata = snapshot_manager.snapshots[snapshot_id]
        assert metadata.archived


class TestSnapshotSummary:
    """Test snapshot summary statistics."""

    def test_snapshot_summary_empty(self, snapshot_manager):
        """Test summary with no snapshots."""
        summary = snapshot_manager.get_snapshot_summary()

        assert summary["total_snapshots"] == 0
        assert summary["active_snapshots"] == 0
        assert summary["archived_snapshots"] == 0

    def test_snapshot_summary_populated(self, snapshot_manager, sample_prospect_records):
        """Test summary with snapshots."""
        # Create multiple snapshots
        for i in range(3):
            date = datetime.utcnow() - timedelta(days=i)
            snapshot_manager.create_snapshot(sample_prospect_records, date)

        summary = snapshot_manager.get_snapshot_summary()

        assert summary["total_snapshots"] == 3
        assert summary["active_snapshots"] == 3
        assert summary["archived_snapshots"] == 0
        assert summary["total_records"] == 9


class TestSnapshotsBetweenDates:
    """Test querying snapshots between dates."""

    def test_get_snapshots_between(self, snapshot_manager, sample_prospect_records):
        """Test getting snapshots within date range."""
        # Create snapshots for 5 days
        start_date = datetime(2026, 2, 10)

        for i in range(5):
            current_date = start_date + timedelta(days=i)
            snapshot_manager.create_snapshot(sample_prospect_records, current_date)

        # Query range (first 3 days)
        snapshots = snapshot_manager.get_snapshots_between(
            start_date,
            start_date + timedelta(days=2),
        )

        assert len(snapshots) == 3

    def test_get_snapshots_between_empty_range(self, snapshot_manager, sample_prospect_records):
        """Test querying date range with no snapshots."""
        snapshot_date = datetime(2026, 2, 10)
        snapshot_manager.create_snapshot(sample_prospect_records, snapshot_date)

        # Query different date range
        other_start = datetime(2026, 3, 1)
        other_end = datetime(2026, 3, 10)

        snapshots = snapshot_manager.get_snapshots_between(other_start, other_end)

        assert len(snapshots) == 0


class TestChangeDetection:
    """Test change detection between snapshots."""

    def test_changed_from_previous_detection(self, snapshot_manager, sample_prospect_records):
        """Test detecting changes from previous snapshot."""
        date1 = datetime(2026, 2, 10)
        date2 = datetime(2026, 2, 11)

        # Create first snapshot
        snapshot_manager.create_snapshot(sample_prospect_records, date1)

        # Modify one record for second snapshot
        modified_records = sample_prospect_records.copy()
        modified_records[0]["forty_time"] = 4.7  # Changed

        snapshot_manager.create_snapshot(modified_records, date2)

        # Load second snapshot
        snapshots = snapshot_manager._load_snapshot_by_date(date2)

        # First prospect should be marked as changed
        first_prospect = snapshots[0]
        assert first_prospect.changed_from_previous

        # Other prospects should not be marked as changed
        other_prospect = snapshots[1]
        assert not other_prospect.changed_from_previous
