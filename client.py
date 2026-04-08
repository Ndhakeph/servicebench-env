# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""ServiceBench Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

from .models import ServiceBenchAction, ServiceBenchObservation, ServiceBenchState


class ServiceBenchEnv(
    EnvClient[ServiceBenchAction, ServiceBenchObservation, ServiceBenchState]
):
    """
    Client for the ServiceBench Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> async with ServiceBenchEnv(base_url="http://localhost:8000") as client:
        ...     result = await client.reset()
        ...     print(result.observation.task_description)
        ...
        ...     action = ServiceBenchAction(
        ...         service="user",
        ...         endpoint="/users/lookup",
        ...         method="GET",
        ...         params={"user_id": 42},
        ...     )
        ...     result = await client.step(action)
        ...     print(result.observation.api_response)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = await ServiceBenchEnv.from_docker_image("servicebench-env:latest")
        >>> try:
        ...     result = await client.reset()
        ...     result = await client.step(ServiceBenchAction(service="order", endpoint="/orders/status", params={"order_id": 1}))
        ... finally:
        ...     await client.close()
    """

    def _step_payload(self, action: ServiceBenchAction) -> Dict:
        """
        Convert ServiceBenchAction to JSON payload for step message.

        Args:
            action: ServiceBenchAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {
            "service": action.service,
            "endpoint": action.endpoint,
            "method": action.method,
            "params": action.params,
        }

    def _parse_result(self, payload: Dict) -> StepResult[ServiceBenchObservation]:
        """
        Parse server response into StepResult[ServiceBenchObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with ServiceBenchObservation
        """
        obs_data = payload.get("observation", {})
        observation = ServiceBenchObservation(
            task_description=obs_data.get("task_description", ""),
            api_response=obs_data.get("api_response", {}),
            success=obs_data.get("success", False),
            error_message=obs_data.get("error_message"),
            available_endpoints=obs_data.get("available_endpoints", []),
            task_completed=obs_data.get("task_completed", False),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> ServiceBenchState:
        """
        Parse server response into ServiceBenchState.

        Args:
            payload: JSON response from state request

        Returns:
            ServiceBenchState with episode_id, task_id, step_count, actions_taken, current_score
        """
        return ServiceBenchState(
            episode_id=payload.get("episode_id", ""),
            task_id=payload.get("task_id", 1),
            step_count=payload.get("step_count", 0),
            actions_taken=payload.get("actions_taken", []),
            current_score=payload.get("current_score", 0.0),
        )
