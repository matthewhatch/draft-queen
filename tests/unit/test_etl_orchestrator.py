"""Unit tests for ETL Orchestrator.

Tests for the main ETL pipeline orchestration engine that coordinates
transformers, validation, and loading.
"""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.data_pipeline.etl_orchestrator import (
    ETLOrchestrator,
    ETLExecution,
    ETLStatus,
    ETLPhase,
    TransformerType,
    TransformerExecution,
    PhaseExecution,
)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture
def orchestrator(mock_db):
    """Create ETL orchestrator instance."""
    return ETLOrchestrator(mock_db)


@pytest.fixture
def extraction_id():
    """Create extraction ID."""
    return uuid4()


class TestTransformerExecution:
    """Test TransformerExecution dataclass."""

    def test_create_transformer_execution(self, extraction_id):
        """Test creating transformer execution record."""
        exec = TransformerExecution(
            transformer_type=TransformerType.PFF,
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            status="running",
            records_processed=100,
        )

        assert exec.transformer_type == TransformerType.PFF
        assert exec.extraction_id == extraction_id
        assert exec.records_processed == 100

    def test_transformer_execution_as_dict(self, extraction_id):
        """Test converting transformer execution to dict."""
        exec = TransformerExecution(
            transformer_type=TransformerType.CFR,
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=5.5,
            status="success",
            records_processed=50,
            records_succeeded=50,
            records_failed=0,
        )

        result = exec.as_dict()

        assert result["transformer"] == "cfr"
        assert result["status"] == "success"
        assert result["records_processed"] == 50
        assert result["records_succeeded"] == 50


class TestPhaseExecution:
    """Test PhaseExecution dataclass."""

    def test_create_phase_execution(self, extraction_id):
        """Test creating phase execution record."""
        phase = PhaseExecution(
            phase=ETLPhase.EXTRACT,
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            status="running",
        )

        assert phase.phase == ETLPhase.EXTRACT
        assert phase.status == "running"

    def test_phase_execution_as_dict(self, extraction_id):
        """Test converting phase execution to dict."""
        phase = PhaseExecution(
            phase=ETLPhase.TRANSFORM,
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=10.5,
            status="success",
            details={"transformers": 3},
        )

        result = phase.as_dict()

        assert result["phase"] == "transform"
        assert result["status"] == "success"
        assert result["details"]["transformers"] == 3


class TestETLExecution:
    """Test ETLExecution dataclass."""

    def test_create_etl_execution(self, extraction_id):
        """Test creating ETL execution record."""
        exec = ETLExecution(
            execution_id="test_001",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        assert exec.execution_id == "test_001"
        assert exec.extraction_id == extraction_id
        assert exec.overall_status == "pending"

    def test_etl_execution_as_dict(self, extraction_id):
        """Test converting ETL execution to dict."""
        exec = ETLExecution(
            execution_id="test_002",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=120.0,
            overall_status="success",
            total_prospects_loaded=500,
            total_grades_loaded=450,
            total_measurements_loaded=350,
            total_stats_loaded=400,
            quality_score=95.5,
        )

        result = exec.as_dict()

        assert result["status"] == "success"
        assert result["prospects_loaded"] == 500
        assert result["quality_score"] == 95.5
        assert result["duration_seconds"] == 120.0

    def test_etl_execution_with_phases(self, extraction_id):
        """Test ETL execution with phase records."""
        phase1 = PhaseExecution(
            phase=ETLPhase.EXTRACT,
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            status="success",
        )
        phase2 = PhaseExecution(
            phase=ETLPhase.TRANSFORM,
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            status="success",
        )

        exec = ETLExecution(
            execution_id="test_003",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
            phases=[phase1, phase2],
        )

        assert len(exec.phases) == 2
        assert exec.phases[0].phase == ETLPhase.EXTRACT
        assert exec.phases[1].phase == ETLPhase.TRANSFORM


class TestETLOrchestrator:
    """Test ETLOrchestrator class."""

    def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.db is not None
        assert orchestrator.transformers == {}
        assert orchestrator.max_records_per_batch == 1000
        assert orchestrator.timeout_seconds == 1800

    def test_orchestrator_custom_config(self, mock_db):
        """Test orchestrator with custom configuration."""
        orch = ETLOrchestrator(
            mock_db,
            max_records_per_batch=500,
            timeout_seconds=3600,
        )

        assert orch.max_records_per_batch == 500
        assert orch.timeout_seconds == 3600

    def test_orchestrator_with_transformers(self, mock_db):
        """Test orchestrator with registered transformers."""
        transformers = {
            TransformerType.PFF: MagicMock(),
            TransformerType.CFR: MagicMock(),
        }

        orch = ETLOrchestrator(mock_db, transformers=transformers)

        assert len(orch.transformers) == 2
        assert TransformerType.PFF in orch.transformers

    def test_orchestrator_with_validator(self, mock_db):
        """Test orchestrator with validator."""
        validator = MagicMock()
        orch = ETLOrchestrator(mock_db, validator=validator)

        assert orch.validator is not None

    async def test_execute_extraction_phases(self, orchestrator, extraction_id):
        """Test that execute_extraction creates phase records."""
        # Mock database results
        mock_result = MagicMock()
        mock_result.fetchall = AsyncMock(return_value=[])
        orchestrator.db.execute = AsyncMock(return_value=mock_result)
        orchestrator.db.commit = AsyncMock()

        execution = await orchestrator.execute_extraction(extraction_id)

        assert execution.extraction_id == extraction_id
        assert len(execution.phases) > 0
        assert execution.completed_at is not None

    async def test_extract_phase_execution(self, orchestrator, extraction_id):
        """Test extract phase specifically."""
        mock_result = MagicMock()
        mock_result.__aiter__ = AsyncMock(return_value=iter([]))
        orchestrator.db.execute = AsyncMock(return_value=mock_result)

        execution = ETLExecution(
            execution_id="test_extract",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orchestrator._execute_extract_phase(execution, extraction_id)

        assert len(execution.phases) == 1
        assert execution.phases[0].phase == ETLPhase.EXTRACT

    async def test_transform_phase_no_transformers(
        self, orchestrator, extraction_id
    ):
        """Test transform phase with no transformers configured."""
        execution = ETLExecution(
            execution_id="test_transform",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orchestrator._execute_transform_phase(
            execution, extraction_id, []
        )

        assert len(execution.phases) == 1
        assert execution.phases[0].phase == ETLPhase.TRANSFORM
        assert execution.phases[0].status == "success"

    async def test_validate_phase_no_validator(self, orchestrator, extraction_id):
        """Test validate phase when no validator configured."""
        execution = ETLExecution(
            execution_id="test_validate",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orchestrator._execute_validate_phase(execution, extraction_id)

        assert len(execution.phases) == 1
        assert execution.phases[0].phase == ETLPhase.VALIDATE
        assert execution.phases[0].status == "skipped"

    async def test_validate_phase_with_validator(self, mock_db, extraction_id):
        """Test validate phase with validator configured."""
        validator = MagicMock()
        report = MagicMock()
        report.overall_status = "PASS"
        report.total_records_evaluated = 1000
        report.quality_metrics = {"completeness": 98.5}
        report.get_pass_rate = MagicMock(return_value=98.5)
        validator.run_all_validations = AsyncMock(return_value=report)
        validator.store_quality_report = AsyncMock(return_value=True)

        orch = ETLOrchestrator(mock_db, validator=validator)

        execution = ETLExecution(
            execution_id="test_validate_with",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orch._execute_validate_phase(execution, extraction_id)

        assert len(execution.phases) == 1
        assert execution.phases[0].status == "success"
        assert execution.quality_score == 98.5

    async def test_merge_phase_execution(self, orchestrator, extraction_id):
        """Test merge phase execution."""
        mock_result = AsyncMock()
        mock_result.fetchone = AsyncMock(return_value=(500, 450, 350, 400))
        orchestrator.db.execute = AsyncMock(return_value=mock_result)

        execution = ETLExecution(
            execution_id="test_merge",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orchestrator._execute_merge_phase(execution, extraction_id)

        assert len(execution.phases) == 1
        assert execution.phases[0].phase == ETLPhase.MERGE
        assert execution.total_prospects_loaded == 500
        assert execution.total_grades_loaded == 450

    async def test_load_phase_success(self, orchestrator, extraction_id):
        """Test load phase succeeds."""
        orchestrator.db.commit = AsyncMock()

        execution = ETLExecution(
            execution_id="test_load",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orchestrator._execute_load_phase(execution, extraction_id)

        assert len(execution.phases) == 1
        assert execution.phases[0].phase == ETLPhase.LOAD
        assert execution.phases[0].status == "success"
        orchestrator.db.commit.assert_called_once()

    async def test_load_phase_failure_rollback(self, orchestrator, extraction_id):
        """Test load phase rolls back on failure."""
        orchestrator.db.commit = AsyncMock(
            side_effect=Exception("DB error")
        )
        orchestrator.db.rollback = AsyncMock()

        execution = ETLExecution(
            execution_id="test_load_fail",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orchestrator._execute_load_phase(execution, extraction_id)

        assert execution.phases[0].status == "failed"
        orchestrator.db.rollback.assert_called_once()

    async def test_publish_phase_execution(self, orchestrator, extraction_id):
        """Test publish phase execution."""
        orchestrator.db.execute = AsyncMock()

        execution = ETLExecution(
            execution_id="test_publish",
            extraction_id=extraction_id,
            started_at=datetime.utcnow(),
        )

        await orchestrator._execute_publish_phase(execution, extraction_id)

        assert len(execution.phases) == 1
        assert execution.phases[0].phase == ETLPhase.PUBLISH
        assert execution.phases[0].status == "success"

    def test_execution_history_tracking(self, orchestrator):
        """Test execution history is tracked."""
        execution = ETLExecution(
            execution_id="test_001",
            extraction_id=uuid4(),
            started_at=datetime.utcnow(),
            overall_status="success",
        )

        orchestrator.execution_history.append(execution)

        history = orchestrator.get_execution_history(limit=10)

        assert len(history) == 1
        assert history[0].execution_id == "test_001"

    def test_execution_summary_calculation(self, orchestrator):
        """Test execution summary statistics."""
        for i in range(3):
            execution = ETLExecution(
                execution_id=f"test_{i:03d}",
                extraction_id=uuid4(),
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=10.0 + i,
                overall_status="success" if i > 0 else "failed",
            )
            orchestrator.execution_history.append(execution)

        summary = orchestrator.get_execution_summary()

        assert summary["total_executions"] == 3
        assert summary["successful_executions"] == 2
        assert summary["failed_executions"] == 1
        assert abs(summary["success_rate"] - 66.67) < 1.0

    def test_execution_summary_empty_history(self, orchestrator):
        """Test execution summary with no history."""
        summary = orchestrator.get_execution_summary()

        assert summary["total_executions"] == 0
        assert summary["successful_executions"] == 0
        assert summary["success_rate"] == 0.0


class TestETLPhases:
    """Test ETL phases enum."""

    def test_all_phases_defined(self):
        """Test all ETL phases are defined."""
        phases = list(ETLPhase)

        assert ETLPhase.EXTRACT in phases
        assert ETLPhase.TRANSFORM in phases
        assert ETLPhase.VALIDATE in phases
        assert ETLPhase.MERGE in phases
        assert ETLPhase.LOAD in phases
        assert ETLPhase.PUBLISH in phases

    def test_phase_ordering(self):
        """Test phases have correct logical order."""
        phases = list(ETLPhase)

        extract_idx = phases.index(ETLPhase.EXTRACT)
        transform_idx = phases.index(ETLPhase.TRANSFORM)
        validate_idx = phases.index(ETLPhase.VALIDATE)
        load_idx = phases.index(ETLPhase.LOAD)

        assert extract_idx < transform_idx
        assert transform_idx < validate_idx
        assert validate_idx < load_idx


class TestTransformerTypes:
    """Test transformer type enum."""

    def test_all_transformers_defined(self):
        """Test all transformer types are defined."""
        types = list(TransformerType)

        assert TransformerType.PFF in types
        assert TransformerType.CFR in types
        assert TransformerType.NFL in types
        assert TransformerType.YAHOO in types

    def test_transformer_values(self):
        """Test transformer type values."""
        assert TransformerType.PFF.value == "pff"
        assert TransformerType.CFR.value == "cfr"
        assert TransformerType.NFL.value == "nfl"
        assert TransformerType.YAHOO.value == "yahoo"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
