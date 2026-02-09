"""Unit tests for pipeline orchestrator."""

import pytest
import asyncio
from datetime import datetime

from data_pipeline.orchestration.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineConnector,
    PipelineStage,
    ExecutionStatus,
    FailureMode,
    StageExecution,
    PipelineExecution,
)


class MockConnector(PipelineConnector):
    """Mock connector for testing."""

    def __init__(
        self,
        records_processed: int = 100,
        records_succeeded: int = 95,
        should_fail: bool = False,
        failure_on_attempt: int = 0,
    ):
        self.records_processed = records_processed
        self.records_succeeded = records_succeeded
        self.should_fail = should_fail
        self.failure_on_attempt = failure_on_attempt
        self.call_count = 0

    async def execute(self):
        """Mock execute."""
        self.call_count += 1

        # Simulate failure on specific attempt
        if self.should_fail and self.call_count <= self.failure_on_attempt:
            raise Exception(f"Mock failure on attempt {self.call_count}")

        return {
            "records_processed": self.records_processed,
            "records_succeeded": self.records_succeeded,
            "records_failed": self.records_processed - self.records_succeeded,
            "data": {"test": "data"},
            "errors": [],
        }


class TestPipelineOrchestratorBasic:
    """Test basic orchestrator functionality."""

    def test_orchestrator_initialization(self):
        """Test orchestrator initializes correctly."""
        orchestrator = PipelineOrchestrator(
            failure_mode=FailureMode.PARTIAL_SUCCESS,
            max_retries=3,
        )

        assert orchestrator.failure_mode == FailureMode.PARTIAL_SUCCESS
        assert orchestrator.max_retries == 3
        assert len(orchestrator.stages) == 0

    def test_register_stage(self):
        """Test registering a stage."""
        orchestrator = PipelineOrchestrator()
        connector = MockConnector()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, connector, order=1)

        assert PipelineStage.NFLCOM_SCRAPE in orchestrator.stages
        assert orchestrator.stages[PipelineStage.NFLCOM_SCRAPE] == connector

    def test_stage_execution_order(self):
        """Test stages execute in correct order."""
        orchestrator = PipelineOrchestrator()

        # Register in non-sequential order
        orchestrator.register_stage(PipelineStage.RECONCILIATION, MockConnector(), order=3)
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)
        orchestrator.register_stage(PipelineStage.YAHOO_SCRAPE, MockConnector(), order=2)

        # Check order is sorted
        stages = [stage for _, stage in orchestrator.stage_order]
        assert stages == [
            PipelineStage.NFLCOM_SCRAPE,
            PipelineStage.YAHOO_SCRAPE,
            PipelineStage.RECONCILIATION,
        ]


class TestPipelineExecution:
    """Test pipeline execution."""

    @pytest.mark.asyncio
    async def test_simple_execution(self):
        """Test executing a simple pipeline."""
        orchestrator = PipelineOrchestrator()

        connector = MockConnector(records_processed=50, records_succeeded=50)
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, connector, order=1)

        execution = await orchestrator.execute_pipeline(triggered_by="manual")

        assert execution.overall_status == ExecutionStatus.SUCCESS
        assert len(execution.stages) == 1
        assert execution.total_records_processed == 50
        assert execution.total_records_succeeded == 50

    @pytest.mark.asyncio
    async def test_multi_stage_execution(self):
        """Test executing multi-stage pipeline."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(100, 95), order=1)
        orchestrator.register_stage(PipelineStage.YAHOO_SCRAPE, MockConnector(80, 78), order=2)
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, MockConnector(60, 55), order=3)

        execution = await orchestrator.execute_pipeline()

        assert execution.overall_status == ExecutionStatus.SUCCESS
        assert len(execution.stages) == 3
        assert execution.total_records_processed == 240
        assert execution.total_records_succeeded == 228

    @pytest.mark.asyncio
    async def test_execution_with_duration(self):
        """Test execution tracks duration."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)

        execution = await orchestrator.execute_pipeline()

        assert execution.duration_seconds is not None
        assert execution.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_triggered_by_scheduler(self):
        """Test recording trigger source."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)

        execution = await orchestrator.execute_pipeline(triggered_by="scheduler")

        assert execution.triggered_by == "scheduler"

    @pytest.mark.asyncio
    async def test_skip_stages(self):
        """Test skipping stages."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)
        orchestrator.register_stage(PipelineStage.YAHOO_SCRAPE, MockConnector(), order=2)
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, MockConnector(), order=3)

        execution = await orchestrator.execute_pipeline(
            skip_stages=[PipelineStage.YAHOO_SCRAPE]
        )

        assert len(execution.stages) == 3
        skipped = [s for s in execution.stages if s.status == ExecutionStatus.SKIPPED]
        assert len(skipped) == 1
        assert skipped[0].stage == PipelineStage.YAHOO_SCRAPE


class TestFailureHandling:
    """Test failure handling modes."""

    @pytest.mark.asyncio
    async def test_fail_fast_mode(self):
        """Test FAIL_FAST stops pipeline on first failure."""
        orchestrator = PipelineOrchestrator(failure_mode=FailureMode.FAIL_FAST, max_retries=0)

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)
        orchestrator.register_stage(
            PipelineStage.YAHOO_SCRAPE,
            MockConnector(should_fail=True, failure_on_attempt=999),
            order=2,
        )
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, MockConnector(), order=3)

        execution = await orchestrator.execute_pipeline()

        # FAIL_FAST mode should stop execution on first failure
        # Only first two stages are attempted
        assert len(execution.stages) == 2
        assert execution.overall_status == ExecutionStatus.FAILED
        failed = execution.get_failed_stages()
        assert len(failed) == 1
        assert failed[0].stage == PipelineStage.YAHOO_SCRAPE

    @pytest.mark.asyncio
    async def test_partial_success_mode(self):
        """Test PARTIAL_SUCCESS continues after failure."""
        orchestrator = PipelineOrchestrator(failure_mode=FailureMode.PARTIAL_SUCCESS, max_retries=0)

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)
        orchestrator.register_stage(
            PipelineStage.YAHOO_SCRAPE,
            MockConnector(should_fail=True, failure_on_attempt=999),
            order=2,
        )
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, MockConnector(), order=3)

        execution = await orchestrator.execute_pipeline()

        # Should execute all three stages
        assert len(execution.stages) == 3
        assert execution.overall_status == ExecutionStatus.FAILED
        assert len(execution.get_successful_stages()) == 2
        assert len(execution.get_failed_stages()) == 1

    @pytest.mark.asyncio
    async def test_retry_on_transient_failure(self):
        """Test retrying on transient failures."""
        orchestrator = PipelineOrchestrator(max_retries=2, retry_delay_seconds=0)

        # Fail on first attempt, succeed on second
        connector = MockConnector(should_fail=True, failure_on_attempt=1)
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, connector, order=1)

        execution = await orchestrator.execute_pipeline()

        # Should succeed after retry
        assert execution.overall_status == ExecutionStatus.SUCCESS
        assert connector.call_count == 2  # Called twice (failed once, succeeded)
        assert execution.stages[0].retry_count == 1

    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        """Test failure after exhausting retries."""
        orchestrator = PipelineOrchestrator(max_retries=2, retry_delay_seconds=0)

        # Always fail
        connector = MockConnector(should_fail=True, failure_on_attempt=999)
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, connector, order=1)

        execution = await orchestrator.execute_pipeline()

        # Should fail after retries exhausted
        assert execution.overall_status == ExecutionStatus.FAILED
        assert connector.call_count == 3  # Initial + 2 retries
        assert execution.stages[0].status == ExecutionStatus.FAILED


class TestNotifications:
    """Test notification handling."""

    @pytest.mark.asyncio
    async def test_set_notifier(self):
        """Test setting notification handler."""
        orchestrator = PipelineOrchestrator()

        async def mock_notifier(execution, notification_type):
            pass

        orchestrator.set_notifier(mock_notifier)

        assert orchestrator.notifier is not None

    @pytest.mark.asyncio
    async def test_notification_on_success(self):
        """Test notification sent on successful execution."""
        notification_sent = []

        async def capture_notifier(execution, notification_type):
            notification_sent.append(notification_type)

        orchestrator = PipelineOrchestrator()
        orchestrator.set_notifier(capture_notifier)
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)

        execution = await orchestrator.execute_pipeline()

        assert execution.notification_sent
        assert notification_sent[0] == "success"

    @pytest.mark.asyncio
    async def test_notification_on_failure(self):
        """Test notification sent on failed execution."""
        notification_sent = []

        async def capture_notifier(execution, notification_type):
            notification_sent.append(notification_type)

        orchestrator = PipelineOrchestrator(max_retries=0)
        orchestrator.set_notifier(capture_notifier)
        orchestrator.register_stage(
            PipelineStage.NFLCOM_SCRAPE,
            MockConnector(should_fail=True, failure_on_attempt=999),
            order=1,
        )

        execution = await orchestrator.execute_pipeline()

        assert execution.notification_sent
        assert notification_sent[0] == "failure"


class TestExecutionHistory:
    """Test execution history tracking."""

    @pytest.mark.asyncio
    async def test_execution_history_tracking(self):
        """Test executions are tracked."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)

        # Run multiple times
        for _ in range(3):
            await orchestrator.execute_pipeline()

        history = orchestrator.get_execution_history()

        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_execution_history_limit(self):
        """Test execution history limit."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(), order=1)

        # Run multiple times
        for _ in range(5):
            await orchestrator.execute_pipeline()

        history = orchestrator.get_execution_history(limit=2)

        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_execution_summary(self):
        """Test execution summary statistics."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(100, 95), order=1)

        # Run twice successfully
        await orchestrator.execute_pipeline()
        await orchestrator.execute_pipeline()

        summary = orchestrator.get_execution_summary()

        assert summary["total_executions"] == 2
        assert summary["successful_executions"] == 2
        assert summary["failed_executions"] == 0
        assert summary["success_rate"] == 100.0
        assert summary["total_records_processed"] == 200

    @pytest.mark.asyncio
    async def test_stage_health_metrics(self):
        """Test stage health tracking."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, MockConnector(100, 95), order=1)

        # Run multiple times
        await orchestrator.execute_pipeline()
        await orchestrator.execute_pipeline()

        health = orchestrator.get_stage_health(PipelineStage.NFLCOM_SCRAPE)

        assert health["total_executions"] == 2
        assert health["successful"] == 2
        assert health["failed"] == 0
        assert health["success_rate"] == 100.0
        assert health["total_records_processed"] == 200


class TestStageExecution:
    """Test stage execution record."""

    def test_stage_execution_creation(self):
        """Test creating stage execution record."""
        stage_exec = StageExecution(
            stage=PipelineStage.NFLCOM_SCRAPE,
            status=ExecutionStatus.SUCCESS,
            started_at=datetime.utcnow(),
            records_processed=100,
            records_succeeded=95,
        )

        assert stage_exec.stage == PipelineStage.NFLCOM_SCRAPE
        assert stage_exec.status == ExecutionStatus.SUCCESS
        assert stage_exec.records_processed == 100

    def test_stage_execution_to_dict(self):
        """Test converting stage execution to dictionary."""
        stage_exec = StageExecution(
            stage=PipelineStage.NFLCOM_SCRAPE,
            status=ExecutionStatus.SUCCESS,
            started_at=datetime.utcnow(),
        )

        stage_dict = stage_exec.as_dict()

        assert stage_dict["stage"] == "nflcom_scrape"
        assert stage_dict["status"] == "success"


class TestPipelineExecution:
    """Test pipeline execution record."""

    def test_pipeline_execution_creation(self):
        """Test creating pipeline execution record."""
        execution = PipelineExecution(
            execution_id="exec_001",
            triggered_by="manual",
            started_at=datetime.utcnow(),
        )

        assert execution.execution_id == "exec_001"
        assert execution.triggered_by == "manual"
        assert execution.overall_status == ExecutionStatus.PENDING

    def test_get_failed_stages(self):
        """Test retrieving failed stages."""
        execution = PipelineExecution(
            execution_id="exec_001",
            triggered_by="manual",
            started_at=datetime.utcnow(),
        )

        # Add stages
        execution.stages.append(
            StageExecution(
                stage=PipelineStage.NFLCOM_SCRAPE,
                status=ExecutionStatus.SUCCESS,
                started_at=datetime.utcnow(),
            )
        )

        execution.stages.append(
            StageExecution(
                stage=PipelineStage.YAHOO_SCRAPE,
                status=ExecutionStatus.FAILED,
                started_at=datetime.utcnow(),
                error_message="Test failure",
            )
        )

        failed = execution.get_failed_stages()

        assert len(failed) == 1
        assert failed[0].stage == PipelineStage.YAHOO_SCRAPE

    def test_get_successful_stages(self):
        """Test retrieving successful stages."""
        execution = PipelineExecution(
            execution_id="exec_001",
            triggered_by="manual",
            started_at=datetime.utcnow(),
        )

        # Add stages
        execution.stages.append(
            StageExecution(
                stage=PipelineStage.NFLCOM_SCRAPE,
                status=ExecutionStatus.SUCCESS,
                started_at=datetime.utcnow(),
            )
        )

        execution.stages.append(
            StageExecution(
                stage=PipelineStage.YAHOO_SCRAPE,
                status=ExecutionStatus.FAILED,
                started_at=datetime.utcnow(),
            )
        )

        successful = execution.get_successful_stages()

        assert len(successful) == 1
        assert successful[0].stage == PipelineStage.NFLCOM_SCRAPE
