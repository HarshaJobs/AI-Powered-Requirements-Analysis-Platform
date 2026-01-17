"""Metrics collection and monitoring."""

from typing import Optional
from datetime import datetime
from collections import defaultdict

import structlog

from src.config import Settings, get_settings

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """
    Metrics collection system for monitoring platform performance.
    
    Tracks:
    - API request metrics (latency, errors, throughput)
    - LLM usage (tokens, costs)
    - Vector store operations
    - Quality metrics
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize the metrics collector."""
        self.settings = settings or get_settings()
        
        # In-memory metrics storage (TODO: Replace with Prometheus/Cloud Monitoring)
        self._metrics: dict[str, list] = defaultdict(list)
        self._counters: dict[str, int] = defaultdict(int)
        
        logger.info("MetricsCollector initialized")

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: float,
    ) -> None:
        """Record API request metrics."""
        metric = {
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._metrics["requests"].append(metric)
        self._counters[f"requests_{status_code}"] += 1
        
        logger.debug(
            "Request metric recorded",
            endpoint=endpoint,
            status_code=status_code,
            latency_ms=latency_ms,
        )

    def record_llm_usage(
        self,
        model: str,
        tokens_prompt: int,
        tokens_completion: int,
        cost: Optional[float] = None,
    ) -> None:
        """Record LLM token usage and cost."""
        metric = {
            "model": model,
            "tokens_prompt": tokens_prompt,
            "tokens_completion": tokens_completion,
            "tokens_total": tokens_prompt + tokens_completion,
            "cost": cost,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._metrics["llm_usage"].append(metric)
        self._counters["total_tokens"] += tokens_prompt + tokens_completion
        self._counters["total_cost"] += cost or 0.0
        
        logger.debug(
            "LLM usage recorded",
            model=model,
            tokens_total=tokens_prompt + tokens_completion,
            cost=cost,
        )

    def record_operation(
        self,
        operation_type: str,
        duration_ms: float,
        success: bool,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record general operation metrics."""
        metric = {
            "operation_type": operation_type,
            "duration_ms": duration_ms,
            "success": success,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self._metrics["operations"].append(metric)
        
        if success:
            self._counters[f"{operation_type}_success"] += 1
        else:
            self._counters[f"{operation_type}_errors"] += 1

    def get_metrics_summary(self) -> dict:
        """Get summary of all metrics."""
        request_metrics = self._metrics.get("requests", [])
        llm_metrics = self._metrics.get("llm_usage", [])
        
        # Calculate averages
        if request_metrics:
            avg_latency = sum(m["latency_ms"] for m in request_metrics) / len(request_metrics)
            error_rate = sum(1 for m in request_metrics if m["status_code"] >= 400) / len(request_metrics)
        else:
            avg_latency = 0.0
            error_rate = 0.0
        
        if llm_metrics:
            total_tokens = sum(m["tokens_total"] for m in llm_metrics)
            total_cost = sum(m["cost"] or 0.0 for m in llm_metrics)
        else:
            total_tokens = 0
            total_cost = 0.0
        
        return {
            "requests": {
                "total": len(request_metrics),
                "average_latency_ms": round(avg_latency, 2),
                "error_rate": round(error_rate, 4),
                "status_codes": {
                    str(code): self._counters.get(f"requests_{code}", 0)
                    for code in [200, 400, 401, 403, 404, 500]
                },
            },
            "llm_usage": {
                "total_requests": len(llm_metrics),
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 4),
            },
            "operations": {
                key.replace("_success", "").replace("_errors", ""): {
                    "success": self._counters.get(f"{key}_success", 0),
                    "errors": self._counters.get(f"{key}_errors", 0),
                }
                for key in self._counters.keys()
                if "_success" in key or "_errors" in key
            },
        }
