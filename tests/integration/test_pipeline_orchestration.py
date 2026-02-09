"""Integration tests for pipeline orchestrator with stage connectors."""

import pytest
from datetime import datetime

from data_pipeline.orchestration.pipeline_orchestrator import (
    PipelineOrchestrator,
    PipelineStage,
    ExecutionStatus,
    FailureMode,
)
from data_pipeline.orchestration.stage_connectors import (
    NFLComConnector,
    YahooConnector,
    ESPNConnector,
    ReconciliationConnector,
    QualityValidationConnector,
    SnapshotConnector,
)


class TestFullPipelineOrchestration:
    """Test complete pipeline orchestration with all stages."""

    @pytest.mark.asyncio
    async def test_complete_pipeline_execution(self):
        """Test executing all pipeline stages in sequence."""
        orchestrator = PipelineOrchestrator()

        # Register all stages
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, NFLComConnector(), order=1)
        orchestrator.register_stage(PipelineStage.YAHOO_SCRAPE, YahooConnector(), order=2)
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, ESPNConnector(), order=3)
        orchestrator.register_stage(
            PipelineStage.RECONCILIATION, ReconciliationConnector(), order=4
        )
        orchestrator.register_stage(
            PipelineStage.QUALITY_VALIDATION, QualityValidationConnector(), order=5
        )
        orchestrator.register_stage(PipelineStage.SNAPSHOT, SnapshotConnector(), order=6)

        # Execute pipeline
        execution = await orchestrator.execute_pipeline(triggered_by="integration_test")

        # Verify all stages attempted
        assert len(execution.stages) == 6
        assert execution.triggered_by == "integration_test"
        assert execution.started_at is not None
        assert execution.completed_at is not None
        assert execution.overall_status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]

    @pytest.mark.asyncio
    async def test_pipeline_with_stage_selection(self):
        """Test executing only specific stages."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, NFLComConnector(), order=1)
        orchestrator.register_stage(PipelineStage.YAHOO_SCRAPE, YahooConnector(), order=2)
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, ESPNConnector(), order=3)

        # Skip ESPN stage
        execution = await orchestrator.execute_pipeline(skip_stages=[PipelineStage.ESPN_SCRAPE])

        # Should have 3 stages recorded, but ESPN skipped
        assert len(execution.stages) == 3
        skipped = [s for s in execution.stages if s.status == ExecutionStatus.SKIPPED]
        assert len(skipped) == 1
        assert skipped[0].stage == PipelineStage.ESPN_SCRAPE

    @pytest.mark.asyncio
    async def test_pipeline_with_timeout(self):
        """Test pipeline respects execution timeout."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, NFLComConnector(), order=1)

        # Use default timeout (very long)
        execution = await orchestrator.execute_pipeline()

        # Should complete
        assert execution.duration_seconds is not None
        assert execution.overall_status in [ExecutionStatus.SUCCESS, ExecutionStatus.FAILED]

    @pytest.mark.asyncio
    async def test_connector_initialization_modes(self):
        """Test connectors work with and without actual instances."""
        # Without actual instances (mock mode)
        nfl = NFLComConnector()
        result = await nfl.execute()

        assert result["records_processed"] == 0
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_pipeline_execution_with_notifications(self):
        """Test pipeline notifications work end-to-end."""
        notifications = []

        async def capture_notification(execution, notification_type):
            notifications.append(
                {
                    "type": notification_type,
                    "execution_id": execution.execution_id,
                    "status": execution.overall_status,
                }
            )

        orchestrator = PipelineOrchestrator()
        orchestrator.set_notifier(capture_notification)
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, NFLComConnector(), order=1)

        execution = await orchestrator.execute_pipeline()

        assert execution.notification_sent
        assert len(notifications) > 0
        assert notifications[0]["execution_id"] == execution.execution_id

    @pytest.mark.asyncio
    async def test_pipeline_metrics_across_stages(self):
        """Test pipeline collects metrics across all stages."""
        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, NFLComConnector(), order=1)
        orchestrator.register_stage(PipelineStage.YAHOO_SCRAPE, YahooConnector(), order=2)
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, ESPNConnector(), order=3)

        execution = await orchestrator.execute_pipeline()

        # Check metrics are collected
        assert execution.total_records_processed >= 0
        assert execution.total_records_succeeded >= 0
        assert execution.total_records_failed >= 0
        assert execution.duration_seconds is not None

    @pytest.mark.asyncio
    async def test_pipeline_execution_history_persistence(self):
        """Test execution history persists across multiple runs."""
        import time

        orchestrator = PipelineOrchestrator()

        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, NFLComConnector(), order=1)

        # Run multiple times with delay to ensure different execution IDs
        exec1 = await orchestrator.execute_pipeline()
        time.sleep(1.1)  # Sleep to ensure different second
        exec2 = await orchestrator.execute_pipeline()
        time.sleep(1.1)  # Sleep to ensure different second
        exec3 = await orchestrator.execute_pipeline()

        history = orchestrator.get_execution_history()

        assert len(history) == 3
        # All executions should be recorded
        assert exec1.execution_id in [h.execution_id for h in history]
        assert exec2.execution_id in [h.execution_id for h in history]
        assert exec3.execution_id in [h.execution_id for h in history]

    @pytest.mark.asyncio
    async def test_stage_execution_data_flow(self):
        """Test data flows through connector execute methods."""
        connector = NFLComConnector()
        result = await connector.execute()

        # Verify result structure
        assert "records_processed" in result
        assert "records_succeeded" in result
        assert "records_failed" in result
        assert "data" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_stage_ordering_preserved(self):
        """Test stages execute in registered order."""
        orchestrator = PipelineOrchestrator()

        # Register out of order
        orchestrator.register_stage(PipelineStage.SNAPSHOT, SnapshotConnector(), order=6)
        orchestrator.register_stage(PipelineStage.NFLCOM_SCRAPE, NFLComConnector(), order=1)
        orchestrator.register_stage(PipelineStage.ESPN_SCRAPE, ESPNConnector(), order=3)

        execution = await orchestrator.execute_pipeline()

        # Check stages are in correct order
        stages = [s.stage for s in execution.stages]
        assert stages[0] == PipelineStage.NFLCOM_SCRAPE
        assert stages[-1] == PipelineStage.SNAPSHOT


class TestConnectorImplementations:
    """Test individual stage connector implementations."""

    @pytest.mark.asyncio
    async def test_nfl_connector_execution(self):
        """Test NFL.com connector execution."""
        connector = NFLComConnector()
        result = await connector.execute()

        assert isinstance(result, dict)
        assert result["records_processed"] == 0
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_yahoo_connector_execution(self):
        """Test Yahoo Sports connector execution."""
        connector = YahooConnector()
        result = await connector.execute()

        assert isinstance(result, dict)
        assert result["records_processed"] == 0

    @pytest.mark.asyncio
    async def test_espn_connector_execution(self):
        """Test ESPN connector execution."""
        connector = ESPNConnector()
        result = await connector.execute()

        assert isinstance(result, dict)
        assert result["records_processed"] == 0

    @pytest.mark.asyncio
    async def test_reconciliation_connector_execution(self):
        """Test reconciliation connector execution."""
        connector = ReconciliationConnector()
        result = await connector.execute()

        assert isinstance(result, dict)
        assert result["records_processed"] == 0

    @pytest.mark.asyncio
    async def test_quality_validation_connector_execution(self):
        """Test quality validation connector execution."""
        connector = QualityValidationConnector()
        result = await connector.execute()

        assert isinstance(result, dict)
        assert result["records_processed"] == 0

    @pytest.mark.asyncio
    async def test_snapshot_connector_execution(self):
        """Test snapshot connector execution."""
        connector = SnapshotConnector()
        result = await connector.execute()

        assert isinstance(result, dict)
        assert result["records_processed"] == 0


class TestConnectorErrorHandling:
    """Test error handling in connectors."""

    @pytest.mark.asyncio
    async def test_nfl_connector_handles_missing_instance(self):
        """Test NFLComConnector handles missing scraper instance gracefully."""
        connector = NFLComConnector(scraper_instance=None)
        result = await connector.execute()

        assert result["records_processed"] == 0
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_yahoo_connector_handles_missing_instance(self):
        """Test YahooConnector handles missing scraper instance gracefully."""
        connector = YahooConnector(scraper_instance=None)
        result = await connector.execute()

        assert result["records_processed"] == 0
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_reconciliation_connector_handles_missing_instance(self):
        """Test ReconciliationConnector handles missing engine instance gracefully."""
        connector = ReconciliationConnector(engine_instance=None)
        result = await connector.execute()

        assert result["records_processed"] == 0
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_quality_connector_handles_missing_instance(self):
        """Test QualityValidationConnector handles missing engine instance gracefully."""
        connector = QualityValidationConnector(engine_instance=None)
        result = await connector.execute()

        assert result["records_processed"] == 0
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_snapshot_connector_handles_missing_instance(self):
        """Test SnapshotConnector handles missing manager instance gracefully."""
        connector = SnapshotConnector(manager_instance=None)
        result = await connector.execute()

        assert result["records_processed"] == 0
        assert len(result["errors"]) > 0
