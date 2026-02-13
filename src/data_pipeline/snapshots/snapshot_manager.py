"""Historical data snapshot system for temporal versioning of prospect data.

This module implements daily snapshots of prospect data, allowing queries for
historical data as it existed on any past date. Old snapshots are compressed
and archived to cold storage after 90 days.

Enables analysis of how prospect evaluations change over time.
"""

import gzip
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import hashlib


logger = logging.getLogger(__name__)


@dataclass
class SnapshotMetadata:
    """Metadata for a snapshot."""

    snapshot_id: str
    snapshot_date: datetime
    total_records: int
    compressed_size_bytes: Optional[int] = None
    uncompressed_size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    compression_level: int = 9
    archived: bool = False
    archive_location: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    compressed_at: Optional[datetime] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "snapshot_date": self.snapshot_date.isoformat(),
            "total_records": self.total_records,
            "compressed_size_bytes": self.compressed_size_bytes,
            "uncompressed_size_bytes": self.uncompressed_size_bytes,
            "checksum": self.checksum,
            "compression_level": self.compression_level,
            "archived": self.archived,
            "archive_location": self.archive_location,
            "created_at": self.created_at.isoformat(),
            "compressed_at": self.compressed_at.isoformat() if self.compressed_at else None,
        }


@dataclass
class ProspectSnapshot:
    """Single prospect record snapshot with timestamp."""

    prospect_id: str
    snapshot_date: datetime
    data: Dict[str, Any]
    data_hash: Optional[str] = None
    changed_from_previous: bool = False

    def calculate_hash(self) -> str:
        """Calculate hash of prospect data for change detection."""
        data_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def update_hash(self) -> None:
        """Update data hash."""
        self.data_hash = self.calculate_hash()


class SnapshotManager:
    """Manages creation, storage, and retrieval of prospect data snapshots.

    Daily snapshots capture the complete state of prospect data. Supports:
    - Creating daily snapshots of all prospect data
    - Querying historical data as it existed on any date
    - Compression of recent snapshots
    - Archival to cold storage after 90 days
    - Restoration of archived snapshots
    """

    def __init__(
        self,
        snapshot_dir: str = "/tmp/snapshots",
        archive_dir: str = "/tmp/archive",
        archive_after_days: int = 90,
    ):
        """Initialize snapshot manager.

        Args:
            snapshot_dir: Directory for active snapshots
            archive_dir: Directory for archived snapshots
            archive_after_days: Archive snapshots older than this many days
        """
        self.snapshot_dir = Path(snapshot_dir)
        self.archive_dir = Path(archive_dir)
        self.archive_after_days = archive_after_days

        # Create directories
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        self.snapshots: Dict[str, SnapshotMetadata] = {}
        self.active_snapshots: Dict[str, List[ProspectSnapshot]] = {}

    def create_snapshot(
        self,
        prospect_records: List[Dict[str, Any]],
        snapshot_date: Optional[datetime] = None,
    ) -> SnapshotMetadata:
        """Create a snapshot of prospect data.

        Args:
            prospect_records: List of prospect data records
            snapshot_date: Date for the snapshot (defaults to today)

        Returns:
            SnapshotMetadata with snapshot information
        """
        if snapshot_date is None:
            snapshot_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        snapshot_id = f"snapshot_{snapshot_date.strftime('%Y%m%d')}"

        # Create prospect snapshots with hash tracking
        prospect_snapshots = []
        previous_snapshots = self._load_previous_snapshot(snapshot_date - timedelta(days=1))

        for record in prospect_records:
            ps = ProspectSnapshot(
                prospect_id=record.get("prospect_id", ""),
                snapshot_date=snapshot_date,
                data=record,
            )
            ps.update_hash()

            # Check if changed from previous day
            if previous_snapshots:
                prev_record = next(
                    (p for p in previous_snapshots if p.prospect_id == ps.prospect_id), None
                )
                if prev_record and prev_record.data_hash != ps.data_hash:
                    ps.changed_from_previous = True

            prospect_snapshots.append(ps)

        # Serialize to JSON
        snapshot_data = [
            {
                "prospect_id": ps.prospect_id,
                "snapshot_date": ps.snapshot_date.isoformat(),
                "data": ps.data,
                "data_hash": ps.data_hash,
                "changed_from_previous": ps.changed_from_previous,
            }
            for ps in prospect_snapshots
        ]

        snapshot_json = json.dumps(snapshot_data, indent=2)
        uncompressed_size = len(snapshot_json.encode())

        # Write uncompressed snapshot
        snapshot_file = self.snapshot_dir / f"{snapshot_id}.json"
        snapshot_file.write_text(snapshot_json)

        # Create metadata
        metadata = SnapshotMetadata(
            snapshot_id=snapshot_id,
            snapshot_date=snapshot_date,
            total_records=len(prospect_snapshots),
            uncompressed_size_bytes=uncompressed_size,
        )

        self.snapshots[snapshot_id] = metadata
        self.active_snapshots[snapshot_id] = prospect_snapshots

        logger.info(
            f"Created snapshot {snapshot_id}: {len(prospect_snapshots)} records, "
            f"{uncompressed_size} bytes"
        )

        return metadata

    def compress_snapshot(self, snapshot_id: str) -> bool:
        """Compress a snapshot file using gzip.

        Args:
            snapshot_id: ID of snapshot to compress

        Returns:
            True if compression successful
        """
        metadata = self.snapshots.get(snapshot_id)
        if not metadata:
            logger.warning(f"Snapshot {snapshot_id} not found")
            return False

        if metadata.archived:
            logger.info(f"Snapshot {snapshot_id} already archived")
            return True

        snapshot_file = self.snapshot_dir / f"{snapshot_id}.json"
        if not snapshot_file.exists():
            logger.warning(f"Snapshot file {snapshot_file} not found")
            return False

        # Compress
        compressed_file = self.snapshot_dir / f"{snapshot_id}.json.gz"

        try:
            with open(snapshot_file, "rb") as f_in:
                with gzip.open(compressed_file, "wb", compresslevel=metadata.compression_level) as f_out:
                    f_out.writelines(f_in)

            compressed_size = compressed_file.stat().st_size

            # Update metadata
            metadata.compressed_size_bytes = compressed_size
            metadata.compressed_at = datetime.utcnow()

            # Calculate compression ratio
            if metadata.uncompressed_size_bytes:
                ratio = (1 - compressed_size / metadata.uncompressed_size_bytes) * 100
                logger.info(
                    f"Compressed {snapshot_id}: {metadata.uncompressed_size_bytes} -> "
                    f"{compressed_size} bytes ({ratio:.1f}% reduction)"
                )

            # Remove uncompressed file
            snapshot_file.unlink()

            return True
        except Exception as e:
            logger.error(f"Failed to compress {snapshot_id}: {e}")
            return False

    def archive_snapshot(self, snapshot_id: str, archive_location: str) -> bool:
        """Archive a snapshot to cold storage.

        Args:
            snapshot_id: ID of snapshot to archive
            archive_location: S3 path or other storage location

        Returns:
            True if archival successful
        """
        metadata = self.snapshots.get(snapshot_id)
        if not metadata:
            logger.warning(f"Snapshot {snapshot_id} not found")
            return False

        # Ensure snapshot is compressed first
        if metadata.compressed_size_bytes is None:
            self.compress_snapshot(snapshot_id)

        # In production, this would upload to S3/cloud storage
        # For now, move to archive directory
        snapshot_file = self.snapshot_dir / f"{snapshot_id}.json.gz"
        if not snapshot_file.exists():
            logger.warning(f"Compressed snapshot {snapshot_file} not found")
            return False

        try:
            archive_file = self.archive_dir / f"{snapshot_id}.json.gz"
            snapshot_file.rename(archive_file)

            metadata.archived = True
            metadata.archive_location = archive_location

            # Remove from active snapshots
            if snapshot_id in self.active_snapshots:
                del self.active_snapshots[snapshot_id]

            logger.info(f"Archived {snapshot_id} to {archive_location}")
            return True
        except Exception as e:
            logger.error(f"Failed to archive {snapshot_id}: {e}")
            return False

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restore an archived snapshot back to active storage.

        Args:
            snapshot_id: ID of snapshot to restore

        Returns:
            True if restoration successful
        """
        metadata = self.snapshots.get(snapshot_id)
        if not metadata or not metadata.archived:
            logger.warning(f"Snapshot {snapshot_id} is not archived")
            return False

        archive_file = self.archive_dir / f"{snapshot_id}.json.gz"
        if not archive_file.exists():
            logger.warning(f"Archive file {archive_file} not found")
            return False

        try:
            snapshot_file = self.snapshot_dir / f"{snapshot_id}.json.gz"
            archive_file.rename(snapshot_file)

            metadata.archived = False
            metadata.archive_location = None

            logger.info(f"Restored {snapshot_id} from archive")
            return True
        except Exception as e:
            logger.error(f"Failed to restore {snapshot_id}: {e}")
            return False

    def get_historical_data(
        self,
        prospect_id: str,
        as_of_date: datetime,
    ) -> Optional[Dict[str, Any]]:
        """Get prospect data as it existed on a specific date.

        Args:
            prospect_id: Prospect to retrieve
            as_of_date: Date to query

        Returns:
            Prospect data as of that date, or None if not found
        """
        # Normalize date
        as_of_date = as_of_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Load snapshot for that date
        snapshots = self._load_snapshot_by_date(as_of_date)
        if not snapshots:
            logger.info(f"No snapshot found for {as_of_date.date()}")
            return None

        # Find prospect in snapshot
        for ps in snapshots:
            if ps.prospect_id == prospect_id:
                return ps.data

        logger.info(f"Prospect {prospect_id} not found in snapshot for {as_of_date.date()}")
        return None

    def get_prospect_history(
        self,
        prospect_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Tuple[datetime, Dict[str, Any]]]:
        """Get prospect data evolution over time.

        Args:
            prospect_id: Prospect to retrieve
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: today)

        Returns:
            List of (date, data) tuples in chronological order
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        history = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        while current_date <= end_date:
            data = self.get_historical_data(prospect_id, current_date)
            if data:
                history.append((current_date, data))

            current_date += timedelta(days=1)

        return history

    def get_data_as_of_date(
        self,
        as_of_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get all prospect data as it existed on a specific date.

        Args:
            as_of_date: Date to query

        Returns:
            List of prospect records as of that date
        """
        snapshots = self._load_snapshot_by_date(as_of_date)
        if not snapshots:
            return []

        return [ps.data for ps in snapshots]

    def cleanup_old_snapshots(self, older_than_days: Optional[int] = None) -> int:
        """Archive snapshots older than threshold.

        Args:
            older_than_days: Archive snapshots older than this many days

        Returns:
            Number of snapshots archived
        """
        if older_than_days is None:
            older_than_days = self.archive_after_days

        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        archived_count = 0

        for snapshot_id, metadata in list(self.snapshots.items()):
            if metadata.snapshot_date < cutoff_date and not metadata.archived:
                archive_loc = f"s3://prospect-snapshots/{snapshot_id}.json.gz"
                if self.archive_snapshot(snapshot_id, archive_loc):
                    archived_count += 1

        logger.info(f"Archived {archived_count} old snapshots")
        return archived_count

    def get_snapshots_between(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[SnapshotMetadata]:
        """Get all snapshots within a date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of snapshot metadata
        """
        return [
            m
            for m in self.snapshots.values()
            if start_date <= m.snapshot_date <= end_date
        ]

    def get_snapshot_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all snapshots."""
        total_snapshots = len(self.snapshots)
        active_snapshots = sum(1 for m in self.snapshots.values() if not m.archived)
        archived_snapshots = sum(1 for m in self.snapshots.values() if m.archived)

        total_uncompressed = sum(
            m.uncompressed_size_bytes or 0 for m in self.snapshots.values()
        )
        total_compressed = sum(
            m.compressed_size_bytes or 0 for m in self.snapshots.values()
        )

        return {
            "total_snapshots": total_snapshots,
            "active_snapshots": active_snapshots,
            "archived_snapshots": archived_snapshots,
            "total_records": sum(m.total_records for m in self.snapshots.values()),
            "total_uncompressed_size_bytes": total_uncompressed,
            "total_compressed_size_bytes": total_compressed,
            "compression_ratio": (1 - total_compressed / total_uncompressed) * 100
            if total_uncompressed > 0
            else 0,
        }

    # Private methods

    def _load_snapshot_by_date(self, date: datetime) -> Optional[List[ProspectSnapshot]]:
        """Load snapshot for a specific date."""
        snapshot_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        snapshot_id = f"snapshot_{snapshot_date.strftime('%Y%m%d')}"

        # Check active cache
        if snapshot_id in self.active_snapshots:
            return self.active_snapshots[snapshot_id]

        # Try to load from file
        return self._load_snapshot_from_file(snapshot_id)

    def _load_snapshot_from_file(self, snapshot_id: str) -> Optional[List[ProspectSnapshot]]:
        """Load snapshot from JSON file."""
        # Try uncompressed first
        snapshot_file = self.snapshot_dir / f"{snapshot_id}.json"
        if snapshot_file.exists():
            try:
                data = json.loads(snapshot_file.read_text())
                snapshots = [
                    ProspectSnapshot(
                        prospect_id=s["prospect_id"],
                        snapshot_date=datetime.fromisoformat(s["snapshot_date"]),
                        data=s["data"],
                        data_hash=s.get("data_hash"),
                        changed_from_previous=s.get("changed_from_previous", False),
                    )
                    for s in data
                ]
                self.active_snapshots[snapshot_id] = snapshots
                return snapshots
            except Exception as e:
                logger.error(f"Failed to load snapshot {snapshot_file}: {e}")
                return None

        # Try compressed
        compressed_file = self.snapshot_dir / f"{snapshot_id}.json.gz"
        if compressed_file.exists():
            try:
                with gzip.open(compressed_file, "rt") as f:
                    data = json.load(f)
                    snapshots = [
                        ProspectSnapshot(
                            prospect_id=s["prospect_id"],
                            snapshot_date=datetime.fromisoformat(s["snapshot_date"]),
                            data=s["data"],
                            data_hash=s.get("data_hash"),
                            changed_from_previous=s.get("changed_from_previous", False),
                        )
                        for s in data
                    ]
                    self.active_snapshots[snapshot_id] = snapshots
                    return snapshots
            except Exception as e:
                logger.error(f"Failed to load compressed snapshot {compressed_file}: {e}")
                return None

        return None

    def _load_previous_snapshot(
        self,
        date: datetime,
    ) -> Optional[List[ProspectSnapshot]]:
        """Load previous snapshot for change detection."""
        return self._load_snapshot_by_date(date)
