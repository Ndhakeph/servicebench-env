# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""
ServiceBench Environment Implementation.

Simulates three backend API services (UserService, OrderService, InventoryService).
An LLM agent receives a task description and must call the correct services in the
right order to complete it.

Tasks are scored using shaped rewards that reward progress toward the optimal
solution path and penalise irrelevant or repeated calls.

Example (Task 1 — Order Status Lookup):
    >>> env = ServiceBenchEnvironment()
    >>> obs = env.reset(task_id=1)
    >>> print(obs.task_description)
    'Find the current delivery status of order ORD-1005 ...'
    >>>
    >>> from models import ServiceBenchAction
    >>> action = ServiceBenchAction(
    ...     service="user",
    ...     endpoint="/users/lookup",
    ...     method="GET",
    ...     params={"email": "jane.doe@example.com"},
    ... )
    >>> result = env.step(action)
    >>> print(result.observation.api_response)
    {'success': True, 'user': {'id': 'USR-001', ...}}
"""

from __future__ import annotations

import sys
import os
from typing import Any, Optional, Set
from uuid import uuid4

# Allow importing models and mock_services from the parent directory when
# running from within the server/ subdirectory.
_PARENT = os.path.join(os.path.dirname(__file__), "..")
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

try:
    from openenv.core.env_server.interfaces import Environment
except ImportError:
    # Standalone fallback — must still satisfy the abstract interface.
    from abc import ABC, abstractmethod

    class Environment(ABC):  # type: ignore[no-redef]
        def __init__(self, transform=None, rubric=None):
            self.transform = transform
            self.rubric = rubric

        @abstractmethod
        def reset(self, seed=None, episode_id=None, **kwargs): ...

        @abstractmethod
        def step(self, action, timeout_s=None, **kwargs): ...

        @property
        @abstractmethod
        def state(self): ...

from models import (
    ServiceBenchAction,
    ServiceBenchObservation,
    ServiceBenchState,
    StepResult,
)
from mock_services import InventoryService, OrderService, UserService


# ---------------------------------------------------------------------------
# Static catalogue of all endpoints exposed to the agent
# ---------------------------------------------------------------------------

_AVAILABLE_ENDPOINTS = [
    {
        "service": "user",
        "endpoint": "/users/lookup",
        "method": "GET",
        "description": "Look up a user by email or user_id.",
        "params": ["email (str, optional)", "user_id (str, optional) — at least one required"],
    },
    {
        "service": "user",
        "endpoint": "/users/list",
        "method": "GET",
        "description": "List all users (paginated, max 5 per page).",
        "params": ["page (int, default 1)", "per_page (int, default 5, max 5)"],
    },
    {
        "service": "user",
        "endpoint": "/users/update",
        "method": "POST",
        "description": "Update user fields (name, status, or preferences).",
        "params": ["user_id (str, required)", "updates (dict, required)"],
    },
    {
        "service": "order",
        "endpoint": "/orders/lookup",
        "method": "GET",
        "description": "Look up a single order by order_id.",
        "params": ["order_id (str, required)"],
    },
    {
        "service": "order",
        "endpoint": "/orders/by-user",
        "method": "GET",
        "description": "Retrieve all orders placed by a user.",
        "params": ["user_id (str, required)"],
    },
    {
        "service": "order",
        "endpoint": "/orders/update-status",
        "method": "POST",
        "description": "Update the status of an order.",
        "params": ["order_id (str, required)", "new_status (str, required)"],
    },
    {
        "service": "order",
        "endpoint": "/orders/process-refund",
        "method": "POST",
        "description": "Process a refund for an order.",
        "params": ["order_id (str, required)", "amount (float, required)", "reason (str, required)"],
    },
    {
        "service": "inventory",
        "endpoint": "/inventory/lookup",
        "method": "GET",
        "description": "Look up a product by SKU.",
        "params": ["sku (str, required)"],
    },
    {
        "service": "inventory",
        "endpoint": "/inventory/check-stock",
        "method": "GET",
        "description": "Check stock level for a SKU.",
        "params": ["sku (str, required)"],
    },
    {
        "service": "inventory",
        "endpoint": "/inventory/price-history",
        "method": "GET",
        "description": "Get price change history for a SKU.",
        "params": ["sku (str, required)"],
    },
    {
        "service": "inventory",
        "endpoint": "/inventory/update-stock",
        "method": "POST",
        "description": "Adjust stock quantity for a SKU (positive = add, negative = remove).",
        "params": ["sku (str, required)", "adjustment (int, required, non-zero)"],
    },
]

# ---------------------------------------------------------------------------
# Task configurations — add Tasks 2 and 3 here tomorrow
# ---------------------------------------------------------------------------

_TASK_CONFIGS: dict[int, dict[str, Any]] = {
    1: {
        "description": (
            "Find the current delivery status of order ORD-1005 for customer "
            "jane.doe@example.com. Report the order status."
        ),
        # Endpoints that make direct progress toward the solution
        "relevant_endpoints": {
            "/users/lookup",
            "/orders/lookup",
            "/orders/by-user",
        },
        # Endpoints that are completely off-task
        "irrelevant_endpoints": {
            "/users/list",
            "/users/update",
            "/orders/update-status",
            "/orders/process-refund",
            "/inventory/lookup",
            "/inventory/check-stock",
            "/inventory/price-history",
            "/inventory/update-stock",
        },
    },
    2: {
        "description": (
            "Customer jane.doe@example.com reports that item SKU-445 from order ORD-1005 "
            "arrived damaged. Verify the order is eligible for return, check the item was "
            "in the order, process the refund for the damaged item, and update the order "
            "status to 'returned'."
        ),
        "relevant_endpoints": {
            "/users/lookup",
            "/orders/lookup",
            "/orders/by-user",
            "/inventory/lookup",
            "/orders/process-refund",
            "/orders/update-status",
        },
        "irrelevant_endpoints": {
            "/users/list",
            "/users/update",
            "/inventory/check-stock",
            "/inventory/price-history",
            "/inventory/update-stock",
        },
    },
    3: {
        "description": (
            "Customer user USR-003 reports being charged $247.50 for order ORD-1009, "
            "but believes the total should be lower. Investigate the discrepancy across "
            "all services, identify the root cause, apply the correct adjustment, and "
            "document what happened."
        ),
        "relevant_endpoints": {
            "/users/lookup",
            "/orders/lookup",
            "/orders/by-user",
            "/inventory/lookup",
            "/inventory/price-history",
            "/orders/process-refund",
        },
        "irrelevant_endpoints": {
            "/users/list",
            "/users/update",
            "/orders/update-status",
            "/inventory/check-stock",
            "/inventory/update-stock",
        },
    },
}

# Sentinel used to build a hashable action key for duplicate detection.
_SENTINEL = object()


def _action_key(action: ServiceBenchAction) -> tuple:
    """Return a hashable key that uniquely identifies a specific API call."""
    params_frozen = tuple(sorted(action.params.items()))
    return (action.service, action.endpoint, action.method.upper(), params_frozen)


class ServiceBenchEnvironment(Environment):
    """
    A gym-style environment for multi-service API orchestration tasks.

    The agent receives a natural-language task description and a catalogue of
    available endpoints across three mock backend services.  It must plan and
    execute a sequence of API calls that collectively solve the task.

    Reward is shaped per-step to guide learning toward the optimal call sequence;
    a step-count bonus is applied when the task is completed efficiently.
    """

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self) -> None:
        super().__init__()
        self._user_svc = UserService()
        self._order_svc = OrderService()
        self._inventory_svc = InventoryService()

        # Episode-level state
        self._state = ServiceBenchState()
        self._task_cfg: dict[str, Any] = {}

        # Reward-tracking flags (reset each episode)
        self._got_first_success: bool = False
        self._got_user_id: bool = False
        self._got_order_status: bool = False
        self._seen_action_keys: Set[tuple] = set()

        # Task 2 reward-tracking flags
        self._t2_eligibility_confirmed: bool = False
        self._t2_item_verified: bool = False
        self._t2_inventory_checked: bool = False
        self._t2_refund_processed: bool = False
        self._t2_status_updated: bool = False

        # Task 3 reward-tracking flags
        self._t3_user_verified: bool = False
        self._t3_order_looked_up: bool = False
        self._t3_inventory_checked: bool = False
        self._t3_root_cause_identified: bool = False
        self._t3_refund_processed: bool = False
        self._t3_wrong_refund: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,  # noqa: ARG002  deterministic env, seed unused
        episode_id: Optional[str] = None,
        task_id: int = 1,
        **kwargs: Any,
    ) -> ServiceBenchObservation:
        """
        Reset all services to a clean state and configure the active task.

        Args:
            seed: Unused (deterministic environment).
            episode_id: Optional episode identifier; one is generated if omitted.
            task_id: Which task to activate (currently only 1 is implemented).
            **kwargs: Ignored extra arguments.

        Returns:
            Initial ServiceBenchObservation with task description and endpoint catalogue.

        Raises:
            ValueError: If task_id is not in the task catalogue.
        """
        if task_id not in _TASK_CONFIGS:
            raise ValueError(
                f"task_id {task_id!r} not found. "
                f"Available tasks: {sorted(_TASK_CONFIGS)}"
            )

        # Reset services to clean seed data
        self._user_svc.reset()
        self._order_svc.reset()
        self._inventory_svc.reset()

        # Reset episode state
        self._state = ServiceBenchState(
            episode_id=episode_id or str(uuid4()),
            task_id=task_id,
            step_count=0,
            actions_taken=[],
            current_score=0.0,
        )
        self._task_cfg = _TASK_CONFIGS[task_id]

        # Reset reward-tracking flags
        self._got_first_success = False
        self._got_user_id = False
        self._got_order_status = False
        self._seen_action_keys = set()

        # Reset task 2 flags
        self._t2_eligibility_confirmed = False
        self._t2_item_verified = False
        self._t2_inventory_checked = False
        self._t2_refund_processed = False
        self._t2_status_updated = False

        # Reset task 3 flags
        self._t3_user_verified = False
        self._t3_order_looked_up = False
        self._t3_inventory_checked = False
        self._t3_root_cause_identified = False
        self._t3_refund_processed = False
        self._t3_wrong_refund = False

        return ServiceBenchObservation(
            done=False,
            reward=0.0,
            task_description=self._task_cfg["description"],
            api_response={},
            success=True,
            error_message=None,
            available_endpoints=_AVAILABLE_ENDPOINTS,
            task_completed=False,
        )

    def step(
        self,
        action: ServiceBenchAction,
        timeout_s: Optional[float] = None,  # noqa: ARG002  all calls are synchronous
        **kwargs: Any,
    ) -> StepResult:
        """
        Execute one API call and return a StepResult.

        Routing:
            action.service == "user"      → UserService
            action.service == "order"     → OrderService
            action.service == "inventory" → InventoryService

        Args:
            action: The API call to execute.
            timeout_s: Unused (all calls are synchronous and fast).
            **kwargs: Ignored.

        Returns:
            StepResult with observation, reward, done, and info fields.
        """
        self._state.step_count += 1

        # Route to the correct service
        response = self._dispatch(action)
        call_succeeded = bool(response.get("success", False))

        # Calculate shaped reward
        reward = self._calculate_reward(action, response, call_succeeded)
        self._state.current_score = min(1.0, max(0.0, self._state.current_score + reward))

        # Record action in history
        self._state.actions_taken.append(
            {
                "step": self._state.step_count,
                "service": action.service,
                "endpoint": action.endpoint,
                "method": action.method,
                "params": action.params,
                "success": call_succeeded,
                "reward": reward,
            }
        )

        # Check task completion
        task_completed = self._is_task_complete()

        # Apply step-count efficiency bonus on completion
        if task_completed:
            bonus = self._completion_bonus()
            self._state.current_score = min(1.0, self._state.current_score + bonus)
            reward += bonus

        error_msg = response.get("error") if not call_succeeded else None

        obs = ServiceBenchObservation(
            done=task_completed,
            reward=float(reward),
            task_description=self._task_cfg["description"],
            api_response=response,
            success=call_succeeded,
            error_message=error_msg,
            available_endpoints=_AVAILABLE_ENDPOINTS,
            task_completed=task_completed,
        )
        return StepResult(
            observation=obs,
            reward=float(reward),
            done=task_completed,
            info={"step": self._state.step_count, "current_score": self._state.current_score},
        )

    @property
    def state(self) -> ServiceBenchState:
        """Return the current episode state."""
        return self._state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _dispatch(self, action: ServiceBenchAction) -> dict:
        """Route the action to the appropriate mock service."""
        svc = action.service.lower()
        if svc == "user":
            return self._user_svc.handle_request(action.endpoint, action.method, action.params)
        if svc == "order":
            return self._order_svc.handle_request(action.endpoint, action.method, action.params)
        if svc == "inventory":
            return self._inventory_svc.handle_request(action.endpoint, action.method, action.params)
        return {
            "success": False,
            "error": f"Unknown service: {action.service!r}. Must be 'user', 'order', or 'inventory'.",
            "code": 400,
        }

    def _calculate_reward(
        self,
        action: ServiceBenchAction,
        response: dict,
        call_succeeded: bool,
    ) -> float:
        """
        Return the shaped reward for the current step (Task 1).

        Reward components
        -----------------
        -0.10  repeating the exact same API call
        -0.05  calling a completely irrelevant endpoint
        +0.15  first successful call to any correct service (one-time)
        +0.30  successfully looking up the user and retrieving user_id (one-time)
        +0.45  successfully retrieving the order status for ORD-1005 (one-time)

        The step-count efficiency bonus is applied separately at completion time.
        The cumulative score is clamped to [0.0, 1.0] by the caller.
        """
        task_id = self._state.task_id
        if task_id == 1:
            return self._reward_task1(action, response, call_succeeded)
        if task_id == 2:
            return self._reward_task2(action, response, call_succeeded)
        if task_id == 3:
            return self._reward_task3(action, response, call_succeeded)

        return 0.0

    def _reward_task1(
        self,
        action: ServiceBenchAction,
        response: dict,  # noqa: ARG002  available for future sub-checks; not needed for Task 1
        call_succeeded: bool,
    ) -> float:
        reward = 0.0
        key = _action_key(action)

        # Penalty for repeating the exact same call
        if key in self._seen_action_keys:
            return -0.10
        self._seen_action_keys.add(key)

        endpoint = action.endpoint
        is_relevant = endpoint in self._task_cfg["relevant_endpoints"]

        if not call_succeeded:
            # Penalise calls to wholly irrelevant endpoints even if they fail
            if not is_relevant:
                reward -= 0.05
            return reward

        # --- successful call below this line ---

        if not is_relevant:
            # Successful but off-task endpoint
            reward -= 0.05
            return reward

        # First correct service call bonus (one-time)
        if not self._got_first_success:
            reward += 0.15
            self._got_first_success = True

        # Successfully looked up the user (any successful /users/lookup)
        if endpoint == "/users/lookup" and not self._got_user_id:
            reward += 0.30
            self._got_user_id = True

        # Successfully retrieved order status for ORD-1005
        if not self._got_order_status:
            if endpoint == "/orders/lookup":
                if action.params.get("order_id") == "ORD-1005":
                    reward += 0.45
                    self._got_order_status = True
            elif endpoint == "/orders/by-user":
                # /orders/by-user returns all of jane.doe's orders, which includes
                # ORD-1005 and its status — counts as retrieving the order status.
                if action.params.get("user_id") == "USR-001":
                    reward += 0.45
                    self._got_order_status = True

        return reward

    def _reward_task2(
        self,
        action: ServiceBenchAction,
        response: dict,
        call_succeeded: bool,
    ) -> float:
        """
        Return the shaped reward for the current step (Task 2).

        Reward components
        -----------------
        -0.10  repeating the exact same API call
        -0.05  calling an irrelevant endpoint
        +0.05  each relevant API call that advances the investigation
        +0.15  confirming return eligibility (order lookup for ORD-1005 with return_eligible=True)
        +0.15  verifying SKU-445 is present in the order items
        +0.10  checking inventory/price for SKU-445
        +0.25  processing refund with correct amount ($49.99) for ORD-1005
        +0.20  updating order status to "returned" for ORD-1005
        -0.10  processing refund with wrong amount
        -0.15  processing refund without first confirming return eligibility
        """
        reward = 0.0
        key = _action_key(action)

        if key in self._seen_action_keys:
            return -0.10
        self._seen_action_keys.add(key)

        endpoint = action.endpoint
        is_relevant = endpoint in self._task_cfg["relevant_endpoints"]

        if not call_succeeded:
            if not is_relevant:
                reward -= 0.05
            return reward

        # Successful call below this line
        if not is_relevant:
            reward -= 0.05
            return reward

        # Base reward for each relevant call that advances the investigation
        reward += 0.05

        # +0.15 for confirming return eligibility; also check item presence in same response
        if endpoint == "/orders/lookup" and action.params.get("order_id") == "ORD-1005":
            order = response.get("order", {})
            if order.get("return_eligible") and not self._t2_eligibility_confirmed:
                reward += 0.15
                self._t2_eligibility_confirmed = True
            # +0.15 for verifying SKU-445 is in the order
            if not self._t2_item_verified:
                items = order.get("items", [])
                if any(item.get("sku") == "SKU-445" for item in items):
                    reward += 0.15
                    self._t2_item_verified = True

        # +0.10 for checking inventory/price for SKU-445
        if endpoint == "/inventory/lookup" and not self._t2_inventory_checked:
            if action.params.get("sku") == "SKU-445":
                reward += 0.10
                self._t2_inventory_checked = True

        # Refund processing
        if endpoint == "/orders/process-refund":
            if action.params.get("order_id") == "ORD-1005":
                # Penalty for skipping eligibility check
                if not self._t2_eligibility_confirmed:
                    reward -= 0.15
                try:
                    amount = float(action.params.get("amount", 0))
                except (TypeError, ValueError):
                    amount = 0.0
                if abs(amount - 49.99) < 0.01:
                    reward += 0.25
                    self._t2_refund_processed = True
                else:
                    reward -= 0.10

        # +0.20 for updating order status to "returned"
        if endpoint == "/orders/update-status" and not self._t2_status_updated:
            if (
                action.params.get("order_id") == "ORD-1005"
                and action.params.get("new_status") == "returned"
            ):
                reward += 0.20
                self._t2_status_updated = True

        return reward

    def _reward_task3(
        self,
        action: ServiceBenchAction,
        response: dict,
        call_succeeded: bool,
    ) -> float:
        """
        Return the shaped reward for the current step (Task 3).

        Reward components
        -----------------
        -0.10  repeating the exact same API call
        -0.05  calling an irrelevant endpoint
        +0.05  each relevant API call that advances the investigation
        +0.10  looking up ORD-1009 and observing items + coupon_applied (one-time)
        +0.10  verifying item prices via inventory service (one-time)
        +0.25  identifying the root cause (order looked up + inventory verified, one-time)
        +0.30  processing the correct adjustment amount ($99.00) for ORD-1009
        -0.15  processing a refund with the wrong amount for ORD-1009

        The step-count efficiency bonus (+0.10 for ≤6 steps) and the no-destructive-errors
        bonus (+0.10) are applied separately at completion time.
        """
        reward = 0.0
        key = _action_key(action)

        if key in self._seen_action_keys:
            return -0.10
        self._seen_action_keys.add(key)

        endpoint = action.endpoint
        is_relevant = endpoint in self._task_cfg["relevant_endpoints"]

        if not call_succeeded:
            if not is_relevant:
                reward -= 0.05
            return reward

        # Successful call below this line
        if not is_relevant:
            reward -= 0.05
            return reward

        # Base reward for each relevant advancing call
        reward += 0.05

        # Track user verification (no extra bonus beyond the base +0.05)
        if endpoint == "/users/lookup" and not self._t3_user_verified:
            resp_user = response.get("user", {})
            if resp_user.get("id") == "USR-003":
                self._t3_user_verified = True

        # +0.10 for looking up ORD-1009 and seeing items + coupon_applied
        if endpoint == "/orders/lookup" and action.params.get("order_id") == "ORD-1009":
            if not self._t3_order_looked_up:
                order = response.get("order", {})
                if order.get("coupon_applied") and order.get("items"):
                    reward += 0.10
                    self._t3_order_looked_up = True

        # /orders/by-user for USR-003 can also surface ORD-1009 with coupon
        if endpoint == "/orders/by-user" and action.params.get("user_id") == "USR-003":
            if not self._t3_order_looked_up:
                orders = response.get("orders", [])
                ord1009 = next((o for o in orders if o.get("id") == "ORD-1009"), None)
                if ord1009 and ord1009.get("coupon_applied") and ord1009.get("items"):
                    reward += 0.10
                    self._t3_order_looked_up = True

        # +0.10 for verifying item prices via inventory (any SKU in ORD-1009)
        if endpoint in ("/inventory/lookup", "/inventory/price-history") and not self._t3_inventory_checked:
            sku = action.params.get("sku")
            if sku in {"SKU-445", "SKU-555", "SKU-312"}:
                reward += 0.10
                self._t3_inventory_checked = True

        # +0.25 for identifying the root cause (requires both order + inventory checks)
        if self._t3_order_looked_up and self._t3_inventory_checked and not self._t3_root_cause_identified:
            reward += 0.25
            self._t3_root_cause_identified = True

        # Refund processing for ORD-1009
        if endpoint == "/orders/process-refund":
            if action.params.get("order_id") == "ORD-1009":
                try:
                    amount = float(action.params.get("amount", 0))
                except (TypeError, ValueError):
                    amount = 0.0
                if abs(amount - 99.00) < 0.01:
                    reward += 0.30
                    self._t3_refund_processed = True
                else:
                    reward -= 0.15
                    self._t3_wrong_refund = True

        return reward

    def _completion_bonus(self) -> float:
        """Return the step-count efficiency bonus applied once on task completion."""
        task_id = self._state.task_id
        steps = self._state.step_count
        if task_id == 1:
            if steps <= 2:
                return 0.10
            if steps == 3:
                return 0.05
            return 0.0
        if task_id == 2:
            return 0.10 if steps <= 5 else 0.0
        if task_id == 3:
            bonus = 0.10 if steps <= 6 else 0.0   # efficiency bonus
            bonus += 0.0 if self._t3_wrong_refund else 0.10  # no destructive errors
            return bonus
        return 0.0

    def _is_task_complete(self) -> bool:
        """Return True when the active task's completion criteria are satisfied."""
        task_id = self._state.task_id
        if task_id == 1:
            # Task complete once the agent has retrieved the order status for ORD-1005.
            return self._got_order_status
        if task_id == 2:
            # Task complete once the refund is processed and status updated to "returned".
            return self._t2_refund_processed and self._t2_status_updated
        if task_id == 3:
            # Task complete once the correct $99.00 adjustment has been processed.
            return self._t3_refund_processed
        return False
