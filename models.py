# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
Data models for the ServiceBench Environment.

ServiceBench simulates three backend API services (UserService, OrderService,
InventoryService). An LLM agent receives a task and must call the right services
in the right order to complete it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

try:
    from openenv.core.env_server import Action, Observation, State
except ImportError:
    # Standalone mode: define lightweight base classes so the module
    # works without the openenv package installed.
    class Action(BaseModel):  # type: ignore[no-redef]
        pass

    class Observation(BaseModel):  # type: ignore[no-redef]
        pass

    class State(BaseModel):  # type: ignore[no-redef]
        pass


class ServiceBenchAction(Action):
    """
    Action for the ServiceBench environment.

    Attributes:
        service: Which backend service to call ("user", "order", "inventory").
        endpoint: The API endpoint path (e.g. "/users/lookup", "/orders/status").
        method: HTTP method to use ("GET", "POST", or "PUT").
        params: Parameters to pass to the API endpoint.
    """

    service: str = Field(..., description='Service to call: "user", "order", or "inventory"')
    endpoint: str = Field(..., description='API endpoint path, e.g. "/users/lookup"')
    method: str = Field(default="GET", description="HTTP method: GET, POST, or PUT")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the API call"
    )


class ServiceBenchObservation(Observation):
    """
    Observation returned after each step in the ServiceBench environment.

    Attributes:
        task_description: The current task the agent must accomplish.
        api_response: The JSON response body from the last API call.
        success: Whether the last API call succeeded.
        error_message: Human-readable error detail if the call failed.
        available_endpoints: All available service endpoints with descriptions.
        task_completed: Whether the overall task has been completed.
    """

    task_description: str = Field(
        default="", description="The task the agent must accomplish"
    )
    api_response: Dict[str, Any] = Field(
        default_factory=dict, description="JSON response from the last API call"
    )
    success: bool = Field(default=False, description="Whether the last API call succeeded")
    error_message: Optional[str] = Field(
        default=None, description="Error message if the API call failed"
    )
    available_endpoints: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="All available service endpoints with their descriptions",
    )
    task_completed: bool = Field(
        default=False, description="Whether the overall task is complete"
    )


class ServiceBenchState(State):
    """
    State for the ServiceBench environment.

    Attributes:
        episode_id: Unique identifier for the current episode.
        task_id: Which task is active (1, 2, or 3).
        step_count: Number of API calls made so far this episode.
        actions_taken: History of API calls made (serialised action dicts).
        current_score: Cumulative reward earned this episode.
    """

    episode_id: str = ""
    task_id: int = Field(default=1, description="Active task index (1, 2, or 3)")
    step_count: int = 0
    actions_taken: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of API calls made this episode"
    )
    current_score: float = 0.0


@dataclass
class StepResult:
    """
    Result returned by the environment after each agent step.

    Attributes:
        observation: The observation visible to the agent after this step.
        reward: Scalar reward signal for the step.
        done: Whether the episode has ended.
        info: Auxiliary diagnostic information (not used for learning).
    """

    observation: ServiceBenchObservation
    reward: float
    done: bool
    info: Dict[str, Any]


__all__ = [
    "ServiceBenchAction",
    "ServiceBenchObservation",
    "ServiceBenchState",
    "StepResult",
]
