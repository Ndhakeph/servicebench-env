"""
mock_services.py — ServiceBench mock data and service logic.

Three services: UserService, OrderService, InventoryService.
All data is hardcoded and deterministic. No external dependencies.
"""

import copy
from datetime import date


# ---------------------------------------------------------------------------
# Seed data — defined once, copied on each reset()
# ---------------------------------------------------------------------------

_USERS_SEED = [
    {
        "id": "USR-001",
        "email": "jane.doe@example.com",
        "name": "Jane Doe",
        "status": "active",
        "created_date": "2022-03-15",
        "preferences": {"newsletter": True, "sms_alerts": False, "language": "en"},
    },
    {
        "id": "USR-002",
        "email": "bob.smith@example.com",
        "name": "Bob Smith",
        "status": "active",
        "created_date": "2021-11-02",
        "preferences": {"newsletter": False, "sms_alerts": True, "language": "en"},
    },
    {
        "id": "USR-003",
        "email": "carol.white@example.com",
        "name": "Carol White",
        "status": "active",
        "created_date": "2023-01-20",
        "preferences": {"newsletter": True, "sms_alerts": True, "language": "en"},
    },
    {
        "id": "USR-004",
        "email": "david.jones@example.com",
        "name": "David Jones",
        "status": "suspended",
        "created_date": "2020-07-08",
        "preferences": {"newsletter": False, "sms_alerts": False, "language": "en"},
    },
    {
        "id": "USR-005",
        "email": "emily.clark@example.com",
        "name": "Emily Clark",
        "status": "active",
        "created_date": "2022-09-30",
        "preferences": {"newsletter": True, "sms_alerts": False, "language": "fr"},
    },
    {
        "id": "USR-006",
        "email": "frank.miller@example.com",
        "name": "Frank Miller",
        "status": "active",
        "created_date": "2023-05-14",
        "preferences": {"newsletter": False, "sms_alerts": True, "language": "en"},
    },
    {
        "id": "USR-007",
        "email": "grace.lee@example.com",
        "name": "Grace Lee",
        "status": "active",
        "created_date": "2021-04-22",
        "preferences": {"newsletter": True, "sms_alerts": True, "language": "zh"},
    },
    {
        "id": "USR-008",
        "email": "henry.wilson@example.com",
        "name": "Henry Wilson",
        "status": "suspended",
        "created_date": "2019-12-01",
        "preferences": {"newsletter": False, "sms_alerts": False, "language": "en"},
    },
    {
        "id": "USR-009",
        "email": "iris.martinez@example.com",
        "name": "Iris Martinez",
        "status": "active",
        "created_date": "2023-08-17",
        "preferences": {"newsletter": True, "sms_alerts": False, "language": "es"},
    },
    {
        "id": "USR-010",
        "email": "jack.taylor@example.com",
        "name": "Jack Taylor",
        "status": "active",
        "created_date": "2022-06-05",
        "preferences": {"newsletter": False, "sms_alerts": True, "language": "en"},
    },
]

_ORDERS_SEED = [
    {
        "id": "ORD-1001",
        "user_id": "USR-002",
        "items": [
            {"sku": "SKU-101", "name": "Wireless Mouse", "quantity": 1, "unit_price": 29.99},
            {"sku": "SKU-203", "name": "USB-C Hub", "quantity": 1, "unit_price": 45.00},
        ],
        "total": 74.99,
        "status": "delivered",
        "created_date": "2026-01-10",
        "return_eligible": False,
    },
    {
        "id": "ORD-1002",
        "user_id": "USR-005",
        "items": [
            {"sku": "SKU-312", "name": "Mechanical Keyboard", "quantity": 1, "unit_price": 119.00},
        ],
        "total": 119.00,
        "status": "shipped",
        "created_date": "2026-03-28",
        "return_eligible": True,
    },
    {
        "id": "ORD-1003",
        "user_id": "USR-001",
        "items": [
            {"sku": "SKU-089", "name": "Laptop Stand", "quantity": 2, "unit_price": 35.50},
        ],
        "total": 71.00,
        "status": "delivered",
        "created_date": "2025-12-20",
        "return_eligible": False,
    },
    {
        "id": "ORD-1004",
        "user_id": "USR-007",
        "items": [
            {"sku": "SKU-555", "name": "Webcam HD", "quantity": 1, "unit_price": 89.99},
            {"sku": "SKU-101", "name": "Wireless Mouse", "quantity": 1, "unit_price": 29.99},
        ],
        "total": 119.98,
        "status": "pending",
        "created_date": "2026-04-05",
        "return_eligible": True,
    },
    {
        # KEY ORDER: jane.doe (USR-001), delivered, contains SKU-445 at $49.99
        "id": "ORD-1005",
        "user_id": "USR-001",
        "items": [
            {"sku": "SKU-445", "name": "Noise-Cancelling Headphones", "quantity": 1, "unit_price": 49.99},
            {"sku": "SKU-203", "name": "USB-C Hub", "quantity": 1, "unit_price": 45.00},
        ],
        "total": 94.99,
        "status": "delivered",
        "created_date": "2026-03-18",
        "return_eligible": True,
    },
    {
        "id": "ORD-1006",
        "user_id": "USR-003",
        "items": [
            {"sku": "SKU-667", "name": "Ergonomic Chair Cushion", "quantity": 1, "unit_price": 54.00},
        ],
        "total": 54.00,
        "status": "returned",
        "created_date": "2026-02-14",
        "return_eligible": False,
    },
    {
        "id": "ORD-1007",
        "user_id": "USR-006",
        "items": [
            {"sku": "SKU-312", "name": "Mechanical Keyboard", "quantity": 1, "unit_price": 119.00},
            {"sku": "SKU-089", "name": "Laptop Stand", "quantity": 1, "unit_price": 35.50},
        ],
        "total": 154.50,
        "status": "delivered",
        "created_date": "2026-01-25",
        "return_eligible": False,
    },
    {
        "id": "ORD-1008",
        "user_id": "USR-009",
        "items": [
            {"sku": "SKU-778", "name": "Monitor Light Bar", "quantity": 1, "unit_price": 39.99},
        ],
        "total": 39.99,
        "status": "shipped",
        "created_date": "2026-04-01",
        "return_eligible": True,
    },
    {
        # KEY ORDER: USR-003, billing discrepancy
        # Stored total: $247.50 — but item sum is $198.00.
        # Coupon "SAVE20" ($49.50 discount) was applied NEGATIVELY
        # (added to total instead of subtracted), inflating the charge.
        "id": "ORD-1009",
        "user_id": "USR-003",
        "items": [
            {"sku": "SKU-445", "name": "Noise-Cancelling Headphones", "quantity": 1, "unit_price": 49.99},
            {"sku": "SKU-555", "name": "Webcam HD", "quantity": 1, "unit_price": 89.99},
            {"sku": "SKU-312", "name": "Mechanical Keyboard", "quantity": 1, "unit_price": 58.02},
        ],
        "total": 247.50,   # BUG: should be 198.00 after SAVE20 coupon (-$49.50)
        "status": "delivered",
        "created_date": "2026-03-10",
        "return_eligible": True,
        "coupon_applied": {"code": "SAVE20", "adjustment": 49.50, "type": "error_positive"},
    },
    {
        "id": "ORD-1010",
        "user_id": "USR-010",
        "items": [
            {"sku": "SKU-889", "name": "Cable Management Kit", "quantity": 3, "unit_price": 12.00},
        ],
        "total": 36.00,
        "status": "delivered",
        "created_date": "2026-03-05",
        "return_eligible": False,
    },
    {
        "id": "ORD-1011",
        "user_id": "USR-001",
        "items": [
            {"sku": "SKU-101", "name": "Wireless Mouse", "quantity": 2, "unit_price": 29.99},
        ],
        "total": 59.98,
        "status": "refunded",
        "created_date": "2025-11-15",
        "return_eligible": False,
    },
    {
        "id": "ORD-1012",
        "user_id": "USR-004",
        "items": [
            {"sku": "SKU-667", "name": "Ergonomic Chair Cushion", "quantity": 2, "unit_price": 54.00},
        ],
        "total": 108.00,
        "status": "pending",
        "created_date": "2026-04-06",
        "return_eligible": True,
    },
    {
        "id": "ORD-1013",
        "user_id": "USR-007",
        "items": [
            {"sku": "SKU-778", "name": "Monitor Light Bar", "quantity": 2, "unit_price": 39.99},
            {"sku": "SKU-889", "name": "Cable Management Kit", "quantity": 1, "unit_price": 12.00},
        ],
        "total": 91.98,
        "status": "delivered",
        "created_date": "2026-02-20",
        "return_eligible": False,
    },
    {
        "id": "ORD-1014",
        "user_id": "USR-002",
        "items": [
            {"sku": "SKU-555", "name": "Webcam HD", "quantity": 1, "unit_price": 89.99},
        ],
        "total": 89.99,
        "status": "shipped",
        "created_date": "2026-04-03",
        "return_eligible": True,
    },
    {
        "id": "ORD-1015",
        "user_id": "USR-005",
        "items": [
            {"sku": "SKU-445", "name": "Noise-Cancelling Headphones", "quantity": 1, "unit_price": 49.99},
            {"sku": "SKU-089", "name": "Laptop Stand", "quantity": 1, "unit_price": 35.50},
        ],
        "total": 85.49,
        "status": "delivered",
        "created_date": "2026-03-22",
        "return_eligible": True,
    },
]

_INVENTORY_SEED = [
    {
        "sku": "SKU-089",
        "name": "Laptop Stand",
        "category": "Accessories",
        "price": 35.50,
        "stock_quantity": 142,
        "price_history": [
            {"date": "2025-06-01", "old_price": 29.99, "new_price": 35.50, "reason": "Cost adjustment"},
        ],
    },
    {
        "sku": "SKU-101",
        "name": "Wireless Mouse",
        "category": "Peripherals",
        "price": 29.99,
        "stock_quantity": 305,
        "price_history": [],
    },
    {
        "sku": "SKU-203",
        "name": "USB-C Hub",
        "category": "Accessories",
        "price": 45.00,
        "stock_quantity": 88,
        "price_history": [
            {"date": "2025-09-15", "old_price": 39.99, "new_price": 45.00, "reason": "Supply chain increase"},
        ],
    },
    {
        "sku": "SKU-312",
        "name": "Mechanical Keyboard",
        "category": "Peripherals",
        "price": 119.00,
        "stock_quantity": 60,
        "price_history": [
            {"date": "2025-03-01", "old_price": 99.00, "new_price": 119.00, "reason": "Component cost increase"},
        ],
    },
    {
        # KEY SKU: current price $49.99, was $39.99 before March 1, 2026
        "sku": "SKU-445",
        "name": "Noise-Cancelling Headphones",
        "category": "Audio",
        "price": 49.99,
        "stock_quantity": 74,
        "price_history": [
            {"date": "2026-03-01", "old_price": 39.99, "new_price": 49.99, "reason": "Market repricing"},
        ],
    },
    {
        "sku": "SKU-555",
        "name": "Webcam HD",
        "category": "Peripherals",
        "price": 89.99,
        "stock_quantity": 47,
        "price_history": [
            {"date": "2025-11-20", "old_price": 79.99, "new_price": 89.99, "reason": "Demand increase"},
        ],
    },
    {
        "sku": "SKU-667",
        "name": "Ergonomic Chair Cushion",
        "category": "Furniture",
        "price": 54.00,
        "stock_quantity": 130,
        "price_history": [],
    },
    {
        "sku": "SKU-778",
        "name": "Monitor Light Bar",
        "category": "Lighting",
        "price": 39.99,
        "stock_quantity": 92,
        "price_history": [
            {"date": "2025-07-10", "old_price": 34.99, "new_price": 39.99, "reason": "Annual adjustment"},
        ],
    },
    {
        "sku": "SKU-889",
        "name": "Cable Management Kit",
        "category": "Accessories",
        "price": 12.00,
        "stock_quantity": 410,
        "price_history": [],
    },
    {
        "sku": "SKU-910",
        "name": "Desk Pad XL",
        "category": "Accessories",
        "price": 27.50,
        "stock_quantity": 200,
        "price_history": [
            {"date": "2025-01-05", "old_price": 22.00, "new_price": 27.50, "reason": "Rebranding"},
        ],
    },
    {
        "sku": "SKU-021",
        "name": "Blue Light Glasses",
        "category": "Eyewear",
        "price": 18.99,
        "stock_quantity": 175,
        "price_history": [],
    },
    {
        "sku": "SKU-132",
        "name": "Wrist Rest Pad",
        "category": "Accessories",
        "price": 14.99,
        "stock_quantity": 220,
        "price_history": [],
    },
    {
        "sku": "SKU-243",
        "name": "Portable SSD 1TB",
        "category": "Storage",
        "price": 109.99,
        "stock_quantity": 55,
        "price_history": [
            {"date": "2025-10-01", "old_price": 129.99, "new_price": 109.99, "reason": "Price drop — competition"},
        ],
    },
    {
        "sku": "SKU-354",
        "name": "HDMI 2.1 Cable 2m",
        "category": "Cables",
        "price": 15.99,
        "stock_quantity": 340,
        "price_history": [],
    },
    {
        "sku": "SKU-465",
        "name": "USB-A to USB-C Adapter",
        "category": "Cables",
        "price": 8.99,
        "stock_quantity": 500,
        "price_history": [],
    },
    {
        "sku": "SKU-576",
        "name": "Wireless Charging Pad",
        "category": "Charging",
        "price": 34.99,
        "stock_quantity": 110,
        "price_history": [
            {"date": "2026-01-15", "old_price": 29.99, "new_price": 34.99, "reason": "Margin adjustment"},
        ],
    },
    {
        "sku": "SKU-687",
        "name": "Laptop Backpack",
        "category": "Bags",
        "price": 74.99,
        "stock_quantity": 68,
        "price_history": [],
    },
    {
        "sku": "SKU-798",
        "name": "Screen Cleaning Kit",
        "category": "Accessories",
        "price": 9.99,
        "stock_quantity": 390,
        "price_history": [],
    },
    {
        "sku": "SKU-809",
        "name": "Mini DisplayPort Adapter",
        "category": "Cables",
        "price": 19.99,
        "stock_quantity": 145,
        "price_history": [],
    },
    {
        "sku": "SKU-920",
        "name": "Smart Power Strip",
        "category": "Power",
        "price": 49.00,
        "stock_quantity": 83,
        "price_history": [
            {"date": "2025-08-20", "old_price": 44.00, "new_price": 49.00, "reason": "Component cost increase"},
        ],
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(data: dict) -> dict:
    return {"success": True, **data}


def _err(message: str, code: int) -> dict:
    return {"success": False, "error": message, "code": code}


def _paginate(items: list, page: int, per_page: int):
    """Return a page slice and pagination metadata."""
    per_page = min(per_page, 5)
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], {
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": max(1, (total + per_page - 1) // per_page),
    }


# ---------------------------------------------------------------------------
# UserService
# ---------------------------------------------------------------------------

class UserService:
    """Manages 10 user profiles with lookup, list, and update endpoints."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._users = copy.deepcopy(_USERS_SEED)
        self._by_id = {u["id"]: u for u in self._users}
        self._by_email = {u["email"]: u for u in self._users}

    # --- /users/lookup ---

    def lookup(self, email: str = None, user_id: str = None) -> dict:
        """
        GET /users/lookup
        Params: email OR user_id (at least one required)
        """
        if not email and not user_id:
            return _err("Missing required param: email or user_id", 400)

        if user_id:
            user = self._by_id.get(user_id)
            if not user:
                return _err(f"User not found: {user_id}", 404)
            return _ok({"user": copy.deepcopy(user)})

        user = self._by_email.get(email)
        if not user:
            return _err(f"User not found: {email}", 404)
        return _ok({"user": copy.deepcopy(user)})

    # --- /users/list ---

    def list(self, page: int = 1, per_page: int = 5) -> dict:
        """
        GET /users/list
        Params: page (default 1), per_page (default 5, max 5)
        """
        try:
            page = int(page)
            per_page = int(per_page)
        except (TypeError, ValueError):
            return _err("Params page and per_page must be integers", 400)

        if page < 1:
            return _err("Param page must be >= 1", 400)
        if per_page < 1:
            return _err("Param per_page must be >= 1", 400)

        page_items, meta = _paginate(self._users, page, per_page)
        return _ok({"users": copy.deepcopy(page_items), "pagination": meta})

    # --- /users/update ---

    def update(self, user_id: str = None, updates: dict = None) -> dict:
        """
        POST /users/update
        Params: user_id (required), updates (dict of fields to set)
        Allowed fields: name, status, preferences
        """
        if not user_id:
            return _err("Missing required param: user_id", 400)
        if not updates or not isinstance(updates, dict):
            return _err("Missing required param: updates (must be a non-empty dict)", 400)

        user = self._by_id.get(user_id)
        if not user:
            return _err(f"User not found: {user_id}", 404)

        ALLOWED = {"name", "status", "preferences"}
        rejected = [k for k in updates if k not in ALLOWED]
        if rejected:
            return _err(f"Fields not updatable: {rejected}. Allowed: {sorted(ALLOWED)}", 400)

        valid_statuses = {"active", "suspended"}
        if "status" in updates and updates["status"] not in valid_statuses:
            return _err(f"Invalid status '{updates['status']}'. Must be one of: {sorted(valid_statuses)}", 400)

        for k, v in updates.items():
            if k == "preferences" and isinstance(v, dict):
                user["preferences"].update(v)
            else:
                user[k] = v

        return _ok({"user": copy.deepcopy(user), "message": "User updated successfully"})

    def handle_request(self, path: str, method: str, params: dict = None) -> dict:
        """Route a request by path and method to the appropriate service method."""
        params = params or {}
        routes = {
            ("/users/lookup",       "GET"):  lambda p: self.lookup(email=p.get("email"), user_id=p.get("user_id")),
            ("/users/list",         "GET"):  lambda p: self.list(page=p.get("page", 1), per_page=p.get("per_page", 5)),
            ("/users/update",       "POST"): lambda p: self.update(user_id=p.get("user_id"), updates=p.get("updates")),
        }
        handler = routes.get((path, method.upper()))
        if handler is None:
            return _err(f"Unknown endpoint: {method.upper()} {path}", 404)
        return handler(params)


# ---------------------------------------------------------------------------
# OrderService
# ---------------------------------------------------------------------------

class OrderService:
    """Manages 15 orders with lookup, user-scoped listing, status updates, and refunds."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._orders = copy.deepcopy(_ORDERS_SEED)
        self._by_id = {o["id"]: o for o in self._orders}
        self._refunds: list[dict] = []

    # --- /orders/lookup ---

    def lookup(self, order_id: str = None) -> dict:
        """
        GET /orders/lookup
        Params: order_id (required)
        """
        if not order_id:
            return _err("Missing required param: order_id", 400)

        order = self._by_id.get(order_id)
        if not order:
            return _err(f"Order not found: {order_id}", 404)
        return _ok({"order": copy.deepcopy(order)})

    # --- /orders/by-user ---

    def by_user(self, user_id: str = None) -> dict:
        """
        GET /orders/by-user
        Params: user_id (required)
        """
        if not user_id:
            return _err("Missing required param: user_id", 400)

        orders = [copy.deepcopy(o) for o in self._orders if o["user_id"] == user_id]
        return _ok({"orders": orders, "count": len(orders), "user_id": user_id})

    # --- /orders/update-status ---

    def update_status(self, order_id: str = None, new_status: str = None) -> dict:
        """
        POST /orders/update-status
        Params: order_id (required), new_status (required)
        """
        if not order_id:
            return _err("Missing required param: order_id", 400)
        if not new_status:
            return _err("Missing required param: new_status", 400)

        valid_statuses = {"pending", "shipped", "delivered", "returned", "refunded"}
        if new_status not in valid_statuses:
            return _err(
                f"Invalid status '{new_status}'. Must be one of: {sorted(valid_statuses)}", 400
            )

        order = self._by_id.get(order_id)
        if not order:
            return _err(f"Order not found: {order_id}", 404)

        old_status = order["status"]
        order["status"] = new_status
        return _ok({
            "order_id": order_id,
            "old_status": old_status,
            "new_status": new_status,
            "message": "Order status updated successfully",
        })

    # --- /orders/process-refund ---

    def process_refund(self, order_id: str = None, amount: float = None, reason: str = None) -> dict:
        """
        POST /orders/process-refund
        Params: order_id (required), amount (required, > 0), reason (required)
        """
        if not order_id:
            return _err("Missing required param: order_id", 400)
        if amount is None:
            return _err("Missing required param: amount", 400)
        if not reason:
            return _err("Missing required param: reason", 400)

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return _err("Param amount must be a number", 400)

        if amount <= 0:
            return _err("Param amount must be greater than 0", 400)

        order = self._by_id.get(order_id)
        if not order:
            return _err(f"Order not found: {order_id}", 404)

        if order["status"] == "refunded":
            return _err(f"Order {order_id} has already been fully refunded", 400)

        if amount > order["total"]:
            return _err(
                f"Refund amount ${amount:.2f} exceeds order total ${order['total']:.2f}", 400
            )

        confirmation_id = f"REF-{len(self._refunds) + 1:04d}"
        refund_record = {
            "confirmation_id": confirmation_id,
            "order_id": order_id,
            "amount": round(amount, 2),
            "reason": reason,
            "processed_date": str(date.today()),
        }
        self._refunds.append(refund_record)
        order["status"] = "refunded"

        return _ok({
            "refund": refund_record,
            "message": f"Refund of ${amount:.2f} processed successfully for order {order_id}",
        })

    def handle_request(self, path: str, method: str, params: dict = None) -> dict:
        """Route a request by path and method to the appropriate service method."""
        params = params or {}
        routes = {
            ("/orders/lookup",        "GET"):  lambda p: self.lookup(order_id=p.get("order_id")),
            ("/orders/by-user",       "GET"):  lambda p: self.by_user(user_id=p.get("user_id")),
            ("/orders/update-status", "POST"): lambda p: self.update_status(order_id=p.get("order_id"), new_status=p.get("new_status")),
            ("/orders/process-refund","POST"): lambda p: self.process_refund(order_id=p.get("order_id"), amount=p.get("amount"), reason=p.get("reason")),
        }
        handler = routes.get((path, method.upper()))
        if handler is None:
            return _err(f"Unknown endpoint: {method.upper()} {path}", 404)
        return handler(params)


# ---------------------------------------------------------------------------
# InventoryService
# ---------------------------------------------------------------------------

class InventoryService:
    """Manages 20 products with lookup, stock checks, price history, and stock adjustments."""

    def __init__(self):
        self.reset()

    def reset(self):
        self._products = copy.deepcopy(_INVENTORY_SEED)
        self._by_sku = {p["sku"]: p for p in self._products}

    # --- /inventory/lookup ---

    def lookup(self, sku: str = None) -> dict:
        """
        GET /inventory/lookup
        Params: sku (required)
        """
        if not sku:
            return _err("Missing required param: sku", 400)

        product = self._by_sku.get(sku)
        if not product:
            return _err(f"Product not found: {sku}", 404)
        return _ok({"product": copy.deepcopy(product)})

    # --- /inventory/check-stock ---

    def check_stock(self, sku: str = None) -> dict:
        """
        GET /inventory/check-stock
        Params: sku (required)
        """
        if not sku:
            return _err("Missing required param: sku", 400)

        product = self._by_sku.get(sku)
        if not product:
            return _err(f"Product not found: {sku}", 404)

        qty = product["stock_quantity"]
        return _ok({
            "sku": sku,
            "name": product["name"],
            "stock_quantity": qty,
            "in_stock": qty > 0,
            "low_stock": 0 < qty <= 10,
        })

    # --- /inventory/price-history ---

    def price_history(self, sku: str = None) -> dict:
        """
        GET /inventory/price-history
        Params: sku (required)
        """
        if not sku:
            return _err("Missing required param: sku", 400)

        product = self._by_sku.get(sku)
        if not product:
            return _err(f"Product not found: {sku}", 404)

        return _ok({
            "sku": sku,
            "name": product["name"],
            "current_price": product["price"],
            "price_history": copy.deepcopy(product["price_history"]),
        })

    # --- /inventory/update-stock ---

    def update_stock(self, sku: str = None, adjustment: int = None) -> dict:
        """
        POST /inventory/update-stock
        Params: sku (required), adjustment (required, non-zero integer; positive = add, negative = remove)
        """
        if not sku:
            return _err("Missing required param: sku", 400)
        if adjustment is None:
            return _err("Missing required param: adjustment", 400)

        try:
            adjustment = int(adjustment)
        except (TypeError, ValueError):
            return _err("Param adjustment must be an integer", 400)

        if adjustment == 0:
            return _err("Param adjustment must be non-zero", 400)

        product = self._by_sku.get(sku)
        if not product:
            return _err(f"Product not found: {sku}", 404)

        new_qty = product["stock_quantity"] + adjustment
        if new_qty < 0:
            return _err(
                f"Adjustment would result in negative stock "
                f"(current: {product['stock_quantity']}, adjustment: {adjustment})",
                400,
            )

        old_qty = product["stock_quantity"]
        product["stock_quantity"] = new_qty
        return _ok({
            "sku": sku,
            "name": product["name"],
            "old_quantity": old_qty,
            "adjustment": adjustment,
            "new_quantity": new_qty,
            "message": "Stock updated successfully",
        })

    def handle_request(self, path: str, method: str, params: dict = None) -> dict:
        """Route a request by path and method to the appropriate service method."""
        params = params or {}
        routes = {
            ("/inventory/lookup",       "GET"):  lambda p: self.lookup(sku=p.get("sku")),
            ("/inventory/check-stock",  "GET"):  lambda p: self.check_stock(sku=p.get("sku")),
            ("/inventory/price-history","GET"):  lambda p: self.price_history(sku=p.get("sku")),
            ("/inventory/update-stock", "POST"): lambda p: self.update_stock(sku=p.get("sku"), adjustment=p.get("adjustment")),
        }
        handler = routes.get((path, method.upper()))
        if handler is None:
            return _err(f"Unknown endpoint: {method.upper()} {path}", 404)
        return handler(params)
