"""ETL Pipeline Orchestrator for coordinating multi-source data ingestion.

Manages the complete data pipeline workflow:
1. NFL.com scraper (combine measurements)
2. Yahoo Sports scraper (college statistics)
3. ESPN scraper (injury data)
4. Data reconciliation (conflict resolution)
5. Quality rules validation (outlier detection)

Supports:
- Scheduled daily execution at configurable time
- Sequential stage execution with failure handling
- Partial success (skip failed stages, continue pipeline)
- Retry logic for transient failures
- Comprehensive logging and metrics
- Email notifications on success/failure
- Manual trigger API
"""

import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Coroutine
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages."""

    NFLCOM_SCRAPE = "nflcom_scrape"
    YAHOO_SCRAPE = "yahoo_scrape"
    ESPN_SCRAPE = "espn_scrape"
    PFF_SCRAPE = "pff_scrape"
    PFF_GRADE_LOAD = "pff_grade_load"
    RECONCILIATION = "reconciliation"
    QUALITY_VALIDATION = "quality_validation"
    SNAPSHOT = "snapshot"


class ExecutionStatus(Enum):
    """Stage execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


class FailureMode(Enum):
    """How pipeline handles failures."""

    FAIL_FAST = "fail_fast"  # Stop entire pipeline on first failure
    PARTIAL_SUCCESS = "partial_success"  # Continue with remaining stages
    RETRY_CONTINUE = "retry_continue"  # Retry failed stage, then continue


@dataclass
class StageExecution:
    """Record of a single stage execution."""

    stage: PipelineStage
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    records_processed: int = 0
    records_succeeded: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    retry_count: int = 0
    skipped_reason: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "records_processed": self.records_processed,
            "records_succeeded": self.records_succeeded,
            "records_failed": self.records_failed,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "skipped_reason": self.skipped_reason,
        }


@dataclass
class PipelineExecution:
    """Complete pipeline execution record."""

    execution_id: str
    triggered_by: str  # "scheduler" or "manual"
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    overall_status: ExecutionStatus = ExecutionStatus.PENDING
    failure_mode: FailureMode = FailureMode.PARTIAL_SUCCESS
    stages: List[StageExecution] = field(default_factory=list)
    total_records_processed: int = 0
    total_records_succeeded: int = 0
    total_records_failed: int = 0
    notification_sent: bool = False
    notification_type: Optional[str] = None  # "success" or "failure"
    error_summary: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "overall_status": self.overall_status.value,
            "failure_mode": self.failure_mode.value,
            "stages": [s.as_dict() for s in self.stages],
            "total_records_processed": self.total_records_processed,
            "total_records_succeeded": self.total_records_succeeded,
            "total_records_failed": self.total_records_failed,
            "notification_sent": self.notification_sent,
            "notification_type": self.notification_type,
            "error_summary": self.error_summary,
        }

    def get_failed_stages(self) -> List[StageExecution]:
        """Get list of failed stages."""
        return [s for s in self.stages if s.status == ExecutionStatus.FAILED]

    def get_successful_stages(self) -> List[StageExecution]:
        """Get list of successful stages."""
        return [s for s in self.stages if s.status == ExecutionStatus.SUCCESS]


class PipelineConnector(ABC):
    """Abstract base for pipeline stage connectors."""

    @abstractmethod
    async def execute(self) -> Dict[str, Any]:
        """Execute stage and return results.

        Returns:
            Dictionary with:
            - records_processed: int
            - records_succeeded: int
            - records_failed: int
            - data: Any (processed data)
            - errors: List[str] (error messages)
        """
        raise NotImplementedError


class PipelineOrchestrator:
    """Main orchestrator for ETL pipeline execution.

    Manages:
    - Stage sequencing and dependencies
    - Error handling and retries
    - Execution logging and metrics
    - Notifications
    - Manual trigger capability
    """

    def __init__(
        self,
        failure_mode: FailureMode = FailureMode.PARTIAL_SUCCESS,
        max_retries: int = 3,
        retry_delay_seconds: int = 5,
        timeout_seconds: int = 3600,
    ):
        """Initialize orchestrator.

        Args:
            failure_mode: How to handle failures
            max_retries: Maximum retry attempts per stage
            retry_delay_seconds: Delay between retries
            timeout_seconds: Overall pipeline timeout
        """
        self.failure_mode = failure_mode
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.timeout_seconds = timeout_seconds

        self.stages: Dict[PipelineStage, PipelineConnector] = {}
        self.stage_order: List[PipelineStage] = []
        self.executions: List[PipelineExecution] = []
        self.notifier: Optional[Callable] = None

    def register_stage(
        self,
        stage: PipelineStage,
        connector: PipelineConnector,
        order: int,
    ) -> None:
        """Register a pipeline stage.

        Args:
            stage: Stage identifier
            connector: Connector implementation
            order: Execution order (lower = earlier)
        """
        self.stages[stage] = connector
        self.stage_order.append((order, stage))
        self.stage_order.sort(key=lambda x: x[0])

        logger.info(f"Registered stage: {stage.value}")

    def set_notifier(self, notifier: Callable) -> None:
        """Set notification callback.

        Args:
            notifier: Async function(execution: PipelineExecution)
        """
        self.notifier = notifier
        logger.info("Notification handler registered")

    async def execute_pipeline(
        self,
        triggered_by: str = "manual",
        skip_stages: Optional[List[PipelineStage]] = None,
    ) -> PipelineExecution:
        """Execute complete pipeline.

        Args:
            triggered_by: Source of trigger ("scheduler" or "manual")
            skip_stages: Stages to skip

        Returns:
            PipelineExecution with complete results
        """
        execution = PipelineExecution(
            execution_id=f"exec_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            triggered_by=triggered_by,
            started_at=datetime.utcnow(),
            failure_mode=self.failure_mode,
        )

        skip_stages = skip_stages or []

        try:
            # Execute stages in order
            for order, stage in self.stage_order:
                if stage in skip_stages:
                    stage_exec = StageExecution(
                        stage=stage,
                        status=ExecutionStatus.SKIPPED,
                        started_at=datetime.utcnow(),
                        skipped_reason="Skipped by request",
                    )
                    execution.stages.append(stage_exec)
                    logger.info(f"Skipped stage: {stage.value}")
                    continue

                stage_exec = await self._execute_stage(stage, execution)
                execution.stages.append(stage_exec)

                # Check failure mode
                if stage_exec.status == ExecutionStatus.FAILED:
                    if self.failure_mode == FailureMode.FAIL_FAST:
                        execution.overall_status = ExecutionStatus.FAILED
                        execution.error_summary = f"Failed at stage: {stage.value}"
                        break
                    elif self.failure_mode == FailureMode.RETRY_CONTINUE:
                        # Retries already handled in _execute_stage
                        pass

            # Aggregate results
            self._aggregate_execution_results(execution)

            # Send notification
            await self._send_notification(execution)

        except asyncio.TimeoutError:
            execution.overall_status = ExecutionStatus.FAILED
            execution.error_summary = f"Pipeline timeout after {self.timeout_seconds}s"
            logger.error(execution.error_summary)
            await self._send_notification(execution)
        except Exception as e:
            execution.overall_status = ExecutionStatus.FAILED
            execution.error_summary = f"Pipeline error: {str(e)}"
            logger.error(execution.error_summary, exc_info=True)
            await self._send_notification(execution)
        finally:
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
            self.executions.append(execution)
            self._log_execution_summary(execution)

        return execution

    async def _execute_stage(
        self,
        stage: PipelineStage,
        execution: PipelineExecution,
    ) -> StageExecution:
        """Execute a single stage with retries.

        Returns:
            StageExecution with results
        """
        stage_exec = StageExecution(
            stage=stage,
            status=ExecutionStatus.PENDING,
            started_at=datetime.utcnow(),
        )

        connector = self.stages[stage]
        last_error = None

        # Attempt with retries
        for attempt in range(self.max_retries + 1):
            try:
                stage_exec.status = ExecutionStatus.RUNNING
                logger.info(f"Executing stage: {stage.value} (attempt {attempt + 1}/{self.max_retries + 1})")

                # Execute with timeout
                result = await asyncio.wait_for(
                    connector.execute(),
                    timeout=self.timeout_seconds,
                )

                # Process results
                stage_exec.status = ExecutionStatus.SUCCESS
                stage_exec.records_processed = result.get("records_processed", 0)
                stage_exec.records_succeeded = result.get("records_succeeded", 0)
                stage_exec.records_failed = result.get("records_failed", 0)

                logger.info(
                    f"Stage {stage.value} completed: "
                    f"{stage_exec.records_succeeded}/{stage_exec.records_processed} records"
                )

                return stage_exec

            except asyncio.TimeoutError:
                last_error = f"Stage timeout after {self.timeout_seconds}s"
                logger.warning(f"{stage.value}: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Stage {stage.value} failed: {last_error}")

            # Delay before retry
            if attempt < self.max_retries:
                stage_exec.retry_count = attempt + 1
                logger.info(f"Retrying {stage.value} after {self.retry_delay_seconds}s...")
                await asyncio.sleep(self.retry_delay_seconds)

        # All retries exhausted
        stage_exec.status = ExecutionStatus.FAILED
        stage_exec.error_message = last_error
        logger.error(f"Stage {stage.value} failed after {self.max_retries + 1} attempts")

        return stage_exec

    def _aggregate_execution_results(self, execution: PipelineExecution) -> None:
        """Aggregate results from all stages."""
        for stage_exec in execution.stages:
            execution.total_records_processed += stage_exec.records_processed
            execution.total_records_succeeded += stage_exec.records_succeeded
            execution.total_records_failed += stage_exec.records_failed

        # Determine overall status
        failed_stages = execution.get_failed_stages()
        if not failed_stages:
            execution.overall_status = ExecutionStatus.SUCCESS
        else:
            execution.overall_status = ExecutionStatus.FAILED

    async def _send_notification(self, execution: PipelineExecution) -> None:
        """Send notification about pipeline execution."""
        if not self.notifier:
            return

        try:
            notification_type = (
                "success" if execution.overall_status == ExecutionStatus.SUCCESS else "failure"
            )

            await self.notifier(execution, notification_type)
            execution.notification_sent = True
            execution.notification_type = notification_type

            logger.info(f"Notification sent: {notification_type}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def _log_execution_summary(self, execution: PipelineExecution) -> None:
        """Log execution summary."""
        summary = f"""
Pipeline Execution Summary
==========================
Execution ID: {execution.execution_id}
Status: {execution.overall_status.value}
Duration: {execution.duration_seconds:.1f}s
Triggered by: {execution.triggered_by}

Records Processed: {execution.total_records_processed}
Records Succeeded: {execution.total_records_succeeded}
Records Failed: {execution.total_records_failed}

Stages Executed: {len(execution.get_successful_stages())}/{len(execution.stages)}
Failed Stages: {len(execution.get_failed_stages())}

Error Summary: {execution.error_summary or 'None'}
Notification Sent: {execution.notification_sent}
"""
        logger.info(summary)

    def get_execution_history(
        self,
        limit: int = 10,
        status_filter: Optional[ExecutionStatus] = None,
    ) -> List[PipelineExecution]:
        """Get recent pipeline executions.

        Args:
            limit: Maximum number of executions to return
            status_filter: Filter by execution status

        Returns:
            List of PipelineExecution records
        """
        executions = self.executions[-limit:]

        if status_filter:
            executions = [e for e in executions if e.overall_status == status_filter]

        return executions

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get overall pipeline statistics."""
        if not self.executions:
            return {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "success_rate": 0.0,
            }

        successful = sum(1 for e in self.executions if e.overall_status == ExecutionStatus.SUCCESS)
        failed = sum(1 for e in self.executions if e.overall_status == ExecutionStatus.FAILED)

        return {
            "total_executions": len(self.executions),
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": (successful / len(self.executions)) * 100 if self.executions else 0,
            "total_records_processed": sum(e.total_records_processed for e in self.executions),
            "total_records_succeeded": sum(e.total_records_succeeded for e in self.executions),
            "total_records_failed": sum(e.total_records_failed for e in self.executions),
        }

    def get_stage_health(self, stage: PipelineStage) -> Dict[str, Any]:
        """Get health metrics for a specific stage."""
        stage_executions = [
            s
            for e in self.executions
            for s in e.stages
            if s.stage == stage
        ]

        if not stage_executions:
            return {"stage": stage.value, "executions": 0}

        successful = sum(1 for s in stage_executions if s.status == ExecutionStatus.SUCCESS)
        failed = sum(1 for s in stage_executions if s.status == ExecutionStatus.FAILED)
        total_duration = sum(s.duration_seconds or 0 for s in stage_executions if s.duration_seconds)
        avg_duration = total_duration / len(stage_executions) if stage_executions else 0

        return {
            "stage": stage.value,
            "total_executions": len(stage_executions),
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / len(stage_executions)) * 100,
            "avg_duration_seconds": avg_duration,
            "total_records_processed": sum(s.records_processed for s in stage_executions),
            "total_records_succeeded": sum(s.records_succeeded for s in stage_executions),
        }
