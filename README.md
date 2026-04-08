---
title: ServiceBench
emoji: 🔧
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# ServiceBench: Multi-Service API Orchestration Environment

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-green)](https://www.python.org/)
[![Live Demo](https://img.shields.io/badge/🤗%20Space-servicebench--env-yellow)](https://huggingface.co/spaces/Tacitus7/servicebench-env)

> **Live environment:** [huggingface.co/spaces/Tacitus7/servicebench-env](https://huggingface.co/spaces/Tacitus7/servicebench-env)

I built ServiceBench because every existing OpenEnv environment I looked at tests agents on a single tool in isolation — one search API, one file system, one calendar. Real backend operations don't work that way. A customer service agent handling a refund has to hit a user service to validate the customer, an order service to check eligibility, and an inventory service to verify the item value — in the right order, with the right parameters, without making unnecessary calls that slow things down or trigger destructive side effects. That's the gap ServiceBench fills.

## 🏗️ Architecture

```
                        ┌─────────────────────────────────────┐
                        │           LLM Agent                 │
                        │  receives task + endpoint catalogue  │
                        └──────────────┬──────────────────────┘
                                       │  ServiceBenchAction
                                       │  {service, endpoint, method, params}
                                       ▼
                        ┌─────────────────────────────────────┐
                        │     ServiceBench Environment        │
                        │   (reward shaping + task tracking)  │
                        └───┬──────────────┬──────────────┬───┘
                            │              │              │
                   ┌────────▼──────┐ ┌─────▼──────┐ ┌───▼────────────┐
                   │  UserService  │ │OrderService│ │InventoryService│
                   │               │ │            │ │                │
                   │ /users/lookup │ │/orders/    │ │/inventory/     │
                   │ /users/list   │ │  lookup    │ │  lookup        │
                   │ /users/update │ │/orders/    │ │/inventory/     │
                   │               │ │  by-user   │ │  check-stock   │
                   │  USR-001 ─────┼─►  ORD-1005 │ │/inventory/     │
                   │  USR-002      │ │  ORD-1009 ─┼─►  SKU-445      │
                   │  USR-003 ─────┼─►  ...      │ │  SKU-555       │
                   └───────────────┘ └────────────┘ └────────────────┘
                         user_id → orders FK    order items → SKU FK
```

The agent must traverse these foreign-key relationships itself. There is no joined query — looking up ORD-1005 without first getting USR-001's `user_id` will fail if the agent tries to use the wrong identifier.

## Environment Description

ServiceBench simulates three interconnected backend microservices with fully deterministic, seeded state that resets cleanly between episodes:

- **UserService** — Customer profiles. Lookup by email or user ID, paginated listing, field updates. `user_id` is the foreign key into OrderService.
- **OrderService** — Purchase orders. Lookup by order ID or user, status updates, refund processing. Line items contain `sku` fields that reference InventoryService.
- **InventoryService** — Product catalog and stock. Lookup by SKU, stock checks, price history, stock adjustments.

The agent receives a natural-language task description and the full endpoint catalogue at episode start. It issues `ServiceBenchAction` calls — one per step — and the environment returns a structured observation with the API response, a success flag, and a running reward. Services enforce realistic error codes: missing required parameters return 400s, nonexistent resources return 404s. An agent that skips a required lookup will not have the IDs it needs for subsequent calls.

## Action Space

```python
class ServiceBenchAction(Action):
    service: str    # "user" | "order" | "inventory"
    endpoint: str   # API path, e.g. "/users/lookup"
    method: str     # "GET" | "POST" | "PUT"  (default: "GET")
    params: dict    # Endpoint-specific parameters (default: {})
```

### UserService

| Endpoint | Method | Description | Parameters |
|---|---|---|---|
| `/users/lookup` | GET | Look up a user by email or ID | `email` (str) or `user_id` (str) — at least one required |
| `/users/list` | GET | List all users, paginated (max 5/page) | `page` (int, default 1), `per_page` (int, default 5) |
| `/users/update` | POST | Update user fields | `user_id` (str, required), `updates` (dict, required) |

### OrderService

| Endpoint | Method | Description | Parameters |
|---|---|---|---|
| `/orders/lookup` | GET | Look up a single order by ID | `order_id` (str, required) |
| `/orders/by-user` | GET | All orders placed by a user | `user_id` (str, required) |
| `/orders/update-status` | POST | Change order status | `order_id` (str, required), `new_status` (str, required) |
| `/orders/process-refund` | POST | Issue a refund | `order_id` (str, required), `amount` (float, required), `reason` (str, required) |

### InventoryService

| Endpoint | Method | Description | Parameters |
|---|---|---|---|
| `/inventory/lookup` | GET | Look up a product by SKU | `sku` (str, required) |
| `/inventory/check-stock` | GET | Current stock level | `sku` (str, required) |
| `/inventory/price-history` | GET | Price change history | `sku` (str, required) |
| `/inventory/update-stock` | POST | Adjust stock quantity | `sku` (str, required), `adjustment` (int, required, non-zero) |

## Observation Space

```python
class ServiceBenchObservation(Observation):
    task_description: str          # Natural-language task the agent must complete
    api_response: dict             # JSON response body from the most recent API call
    success: bool                  # Whether the last call succeeded
    error_message: Optional[str]   # Error detail if the call failed; None on success
    available_endpoints: list      # Full endpoint catalogue with descriptions and params
    task_completed: bool           # True once all completion criteria are met
```

`available_endpoints` is returned on every observation — agents do not need to memorize the API surface.

## Task Descriptions

### Task 1: Order Status Lookup — Easy

**Prompt:** *"Find the current delivery status of order ORD-1005 for customer jane.doe@example.com. Report the order status."*

The agent must resolve the customer email to a `user_id` via UserService, then retrieve the order from OrderService using the order ID. The episode ends when the order status for ORD-1005 is successfully retrieved.

**Optimal path (2 steps):** `/users/lookup` → `/orders/lookup`

**What it tests:** Basic cross-service chaining. The agent must parse a structured API response, extract a field (`user_id`), and pass it as a parameter to the next call. A capable tool-using LLM should complete this reliably — it is the entry-level bar for whether an agent can orchestrate across service boundaries at all.

### Task 2: Process Return and Refund — Medium

**Prompt:** *"Customer jane.doe@example.com reports that item SKU-445 from order ORD-1005 arrived damaged. Verify the order is eligible for return, check the item was in the order, process the refund for the damaged item, and update the order status to 'returned'."*

The agent must: look up the customer, retrieve ORD-1005 and confirm `return_eligible: true` and the presence of SKU-445 in the line items, look up SKU-445 in InventoryService to confirm its value, issue a refund of exactly $49.99, then update the order status to `"returned"`. Skipping the eligibility check before refunding incurs a penalty. Issuing the wrong refund amount also incurs a penalty.

**Optimal path (5 steps):** `/users/lookup` → `/orders/lookup` → `/inventory/lookup` → `/orders/process-refund` → `/orders/update-status`

**What it tests:** Multi-step workflow with conditional verification. The agent must follow a business process in order, validate intermediate results before issuing write operations, and use precise parameter values extracted from prior responses.

### Task 3: Billing Discrepancy Investigation — Hard

**Prompt:** *"Customer USR-003 reports being charged $247.50 for order ORD-1009, but believes the total should be lower. Investigate the discrepancy across all services, identify the root cause, apply the correct adjustment, and document what happened."*

The root cause is that coupon `SAVE20` was applied as an addition instead of a discount, overbilling by $99.00. The agent must correlate data across all three services — user profile, order line items with `coupon_applied` metadata, and InventoryService price records — to independently arrive at the $99.00 figure and issue the correct refund. The correct amount is not stated anywhere; it must be derived. An efficiency bonus rewards reaching the correct answer with minimal redundant exploration, and a precision bonus rewards completing the task without ever issuing a wrong-amount refund.

**Optimal path (4 steps):** `/users/lookup` → `/orders/lookup` → `/inventory/lookup` → `/orders/process-refund`

**What it tests:** Cross-service root cause analysis. This is the hardest task because the agent must reason about numerical discrepancies, synthesize data from all three services, and commit to a specific derived value — not just follow a sequence of steps that are clearly implied by the task description.

## 📊 Reward Design

ServiceBench uses dense reward shaping — every step produces a signal, not just task completion. All per-step rewards accumulate into a running score clamped to `[0.0, 1.0]`.

### Per-Step Signals

| Signal | Value | Condition |
|---|---|---|
| Duplicate call penalty | −0.10 | Exact same (service, endpoint, method, params) repeated |
| Irrelevant endpoint penalty | −0.05 | Called an endpoint with no bearing on the active task |
| First correct call bonus | +0.15 | First successful relevant call (Task 1, one-time) |
| Base progress reward | +0.05 | Each unique, task-relevant successful call (Tasks 2 & 3) |

### Milestone Rewards

**Task 1**

| Milestone | Reward | Condition |
|---|---|---|
| User ID retrieved | +0.30 | Successful `/users/lookup` |
| Order status retrieved | +0.45 | Successful `/orders/lookup` or `/orders/by-user` returning ORD-1005 |

**Task 2**

| Milestone | Reward | Condition |
|---|---|---|
| Return eligibility confirmed | +0.15 | `/orders/lookup` returns `return_eligible: true` for ORD-1005 |
| Item presence verified | +0.15 | SKU-445 found in the order's items list |
| Inventory checked | +0.10 | Successful `/inventory/lookup` for SKU-445 |
| Correct refund issued | +0.25 | `/orders/process-refund` with amount $49.99 (±$0.01) |
| Status updated to returned | +0.20 | `/orders/update-status` → `"returned"` for ORD-1005 |
| Refund before eligibility | −0.15 | Issued refund without first confirming eligibility |
| Wrong refund amount | −0.10 | Refund for ORD-1005 with incorrect amount |

**Task 3**

| Milestone | Reward | Condition |
|---|---|---|
| Order data retrieved | +0.10 | `/orders/lookup` for ORD-1009 with coupon + items present |
| Inventory prices verified | +0.10 | Successful inventory lookup for any SKU in ORD-1009 |
| Root cause identified | +0.25 | Composite — both order and inventory checks completed |
| Correct adjustment issued | +0.30 | `/orders/process-refund` with amount $99.00 (±$0.01) |
| Wrong refund amount | −0.15 | Refund for ORD-1009 with incorrect amount |

### Completion Bonuses

Applied once when task completion criteria are satisfied:

| Task | Bonus | Condition |
|---|---|---|
| Task 1 | +0.10 | Completed in ≤ 2 steps |
| Task 1 | +0.05 | Completed in exactly 3 steps |
| Task 2 | +0.10 | Completed in ≤ 5 steps |
| Task 3 | +0.10 | Completed in ≤ 6 steps (efficiency) |
| Task 3 | +0.10 | No wrong-amount refund at any point (precision) |

### Score Normalization

The cumulative reward is clamped to `[0.0, 1.0]` after every step. A perfect episode — correct call sequence, no duplicates or irrelevant calls, within the step budget — scores `1.0`.

## Baseline Scores

Produced by `python inference.py --fallback`, which executes the hardcoded optimal action sequences deterministically (no LLM required):

| Task | Difficulty | Description | Score |
|---|---|---|---|
| 1 | Easy | Order Status Lookup | 1.0000 |
| 2 | Medium | Process Return and Refund | 1.0000 |
| 3 | Hard | Billing Discrepancy Investigation | 1.0000 |
| — | — | **Mean** | **1.0000** |

These are deterministic optimal-path scores — the fallback replays the exact correct action sequence for each task. An LLM agent operating without hardcoded sequences will typically score lower, particularly on Tasks 2 and 3 where reasoning under partial information is required. Run `python inference.py --fallback` to verify.

## ⚡ Setup & Usage

### Prerequisites

- Python 3.11+
- Docker (for containerized deployment)

### Local Development

```bash
pip install -e .
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

**Try it immediately:**

```bash
# Reset to Task 1
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": 1}'

# Make the first optimal call
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"service": "user", "endpoint": "/users/lookup", "method": "GET", "params": {"email": "jane.doe@example.com"}}'
```

**API routes:**

| Route | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/reset` | POST | Start a clean episode; body: `{"task_id": 1}` |
| `/step` | POST | Execute one `ServiceBenchAction`; returns observation, reward, done, info |
| `/state` | GET | Inspect current episode state |

### Docker

```bash
docker build -t servicebench-env -f server/Dockerfile .
docker run -p 8000:8000 servicebench-env
```

### Running Inference

```bash
export API_BASE_URL="https://api-inference.huggingface.co/models/<model>/v1"
export MODEL_NAME="meta-llama/Llama-3.1-8B-Instruct"
export HF_TOKEN="hf_..."

python inference.py

# Deterministic baseline (no LLM required)
python inference.py --fallback
```

### Project Structure

```
servicebench-env/
├── models.py                        # ServiceBenchAction, ServiceBenchObservation, ServiceBenchState
├── mock_services.py                 # Deterministic UserService, OrderService, InventoryService
├── client.py                        # OpenEnv-compatible client
├── inference.py                     # LLM agent + --fallback optimal sequences
├── server/
│   ├── app.py                       # FastAPI application
│   ├── servicebench_environment.py  # Reward shaping, task completion logic
│   └── Dockerfile
└── openenv.yaml                     # OpenEnv manifest
```

## What I Learned

Building this environment forced me to think carefully about what reward shaping actually teaches. A sparse reward — just 1.0 for task completion — gives almost no learning signal: most episodes end without completion and the gradient is zero. Dense per-step rewards make every call informative, but designing them means committing to a specific "correct" procedure rather than just a correct outcome. That's a real constraint, and it's worth being explicit about: ServiceBench rewards the canonical business process path, not arbitrary paths that happen to retrieve the right data.

The most interesting design decision was the root-cause identification milestone in Task 3. There is no single API call that "identifies the root cause" — the milestone fires when both the order and the inventory data have been retrieved, regardless of order. Rewarding the conjunction of two prior conditions rather than a specific call means the agent is not penalized for approaching the investigation from either direction. It's a better proxy for comprehension than any individual endpoint, and it's the kind of reward shaping that could only come from thinking through the task as a human expert would actually perform it.
