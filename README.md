# Mama AI Tea Shop — Analysis Report

> **Project:** Conversational AI Milk Tea Ordering Bot  
> **Platform:** Telegram · Python · GPT-4o-mini · PayOS · SQLite  
> **Deployment:** Render (Free-tier with Flask keep-alive)  
> **Date:** April 19, 2026  

---

## 1. Project Overview

### 1.1 Original Vision (from SKILL.md)

The project was conceived as a **Vietnamese-language AI chatbot** that assumes the persona of a caring shop-owner mother ("Chị/Mẹ") running a milk tea business. The bot automates the full customer lifecycle:

1. **Menu browsing** — customers ask for the menu and receive a formatted price list  
2. **Natural language ordering** — customers say things like "Cho em 2 ly Trà Sữa Trân Châu Đen size L" and the AI extracts `item_name`, `size`, `quantity`  
3. **Payment via PayOS** — the bot generates a dynamic QR code when the customer says "Tính tiền"  
4. **Admin management** — the shop owner uses Telegram commands to view orders, mark them READY, and delete fulfilled orders  

### 1.2 Stakeholders

| Role | Interface | Capabilities |
|---|---|---|
| **Customer** | Telegram chat with LLM | Browse menu, build cart, create orders, modify/transfer/cancel PENDING orders, request payment QR |
| **Admin/Shop Owner** | Telegram commands (`/view_orders`, `/mark_ready`, etc.) | View all orders, mark PAID orders as READY, add/delete menu items, bulk delete orders |
| **LLM (GPT-4o-mini)** | Internal agent | Interprets natural language, calls Python tool functions, returns Vietnamese responses |
| **PayOS** | External API | Generates payment links, confirms payment via polling |

### 1.3 General Approach

Building a production chatbot that relies on a large language model (LLM) to manage real financial transactions introduces a unique set of challenges that traditional software does not face. Before writing any code, we identified four critical risk areas and established architectural strategies to mitigate each one.

**LLM Unreliability.** The core risk of this system is that the LLM is non-deterministic — it can fabricate item names, invent order IDs, or confidently claim an action was completed when no tool was ever called. Our approach treats the LLM as an *untrusted input layer*: every piece of data the LLM produces (item names, quantities, order references) is validated and resolved by deterministic Python code before it touches the database. The LLM is never given raw database IDs to memorize; instead, it passes natural-language Vietnamese strings that a strict resolver (`_find_item()`) maps to exact database records. This "trust nothing from the LLM" principle became the foundation of the entire tool architecture.

**Deployment Constraints.** The target deployment is Render's free tier, which shuts down services that don't bind to a port or receive HTTP traffic. Since the Telegram bot uses long-polling (not HTTP), it would be killed after the idle timeout. Our solution is a lightweight Flask thread that binds to the Render-assigned `PORT` and responds to health checks, while the Telegram bot runs on the main thread. This keeps the service alive without requiring a paid plan.

**Database & State Management.** We chose SQLite for its zero-configuration simplicity — ideal for a single-instance deployment. However, the system must manage two fundamentally different types of state: the *ephemeral* draft cart (items being added before the customer commits) and the *persistent* order record (saved to the database after finalization). Mixing these would create data corruption if the bot crashes mid-order. Our approach uses a strict two-tier architecture: draft carts live exclusively in RAM (`sessions/cache.py`) and are never written to SQLite until the customer explicitly finalizes. This guarantees that incomplete orders never pollute the database, and if the process restarts, only uncommitted drafts are lost — not confirmed orders.

**Payment Integration.** PayOS provides QR-code-based payments, but payment confirmation is asynchronous — a customer may scan the code minutes after receiving it. We use a 15-second polling job to check PayOS for completed transactions and automatically update order status from PENDING to PAID. This is a pragmatic trade-off: webhook-based confirmation would be more responsive, but requires a publicly accessible endpoint with signature verification, which adds complexity that can be deferred to a future iteration.

---

## 2. Requirements Analysis — SKILL.md vs Actual Implementation

### 2.1 Features Specified in SKILL.md

| # | SKILL.md Requirement | Status | Implementation Notes |
|---|---|---|---|
| 1 | Menu data from `menu.pdf`, validated by LLM | Done | Menu was extracted from PDF via `seed_menu.py` → parsed to `seed_db.py` → seeded into SQLite `menu` table. LLM always calls `get_menu` tool to verify items. |
| 2 | NLP extraction of `item_name`, `size`, `quantity` | Done | OpenAI Function Calling extracts these as structured tool arguments. |
| 3 | Session-based cache for pending orders | Done | `sessions/cache.py` — in-memory dict keyed by `customer_tg_id`. Draft carts live here until finalized to SQLite. |
| 4 | Checkout triggers PayOS QR code | Done | `[CHECKOUT_ORDER] X` tag in LLM output triggers `bot/handlers.py` to call `payos_service.create_payment_link()`. |
| 5 | PayOS webhook/polling for payment verification | Partial | **Polling only** — `main.py` runs `poll_payments()` every 15 seconds. No webhook endpoint implemented yet. |
| 6 | Vietnamese persona ("Mẹ"/"Cô", using "nhé"/"nha") | Deviated | Persona uses **"Chị"** (older sister) instead of "Mẹ"/"Cô" as specified. This was a deliberate adjustment — "Chị" feels more natural for a young shop owner. |
| 7 | Out-of-stock handling | Done | `menu_model.get_all_items(only_available=True)` filters unavailable items. `_find_item()` returns `None` for non-existent items, triggering a polite error. |
| 8 | Modular code with clear logging | Done | 7 Python modules: `bot/`, `llm/`, `database/`, `owner/`, `services/`, `sessions/`, `main.py`. All use Python `logging`. |

### 2.2 Features NOT in SKILL.md but Implemented (from Issue_EN.txt & User Requests)

These features were requested during iterative development and are **missing from SKILL.md**:

| # | Feature | Source | Status |
|---|---|---|---|
| 1 | `recipient_name` + `delivery_time` attributes on orders | Issue_EN.txt #1 | Done |
| 2 | Ability to change delivery time / recipient name | Issue_EN.txt #2 | Done (`update_order_info` tool) |
| 3 | Global `order_name` as `{user_id}_{order_id}` | Issue_EN.txt #3 | Done |
| 4 | Distinguish new order vs. modifying existing order | Issue_EN.txt #4 | Done (DRAFT vs PENDING separation) |
| 5 | Formatted `/view_orders` for admin | Issue_EN.txt #5 | Done |
| 6 | PAID orders: block item modification, allow time changes | Issue_EN.txt #6 | Done |
| 7 | Transfer items between orders | Issue_EN.txt #7 | Done (`transfer_item` tool) |
| 8 | Delete items from specific orders | Issue_EN.txt #8 | Done (`modify_pending_order` with action=remove) |
| 9 | Cancel entire PENDING orders | User request | Done (`cancel_pending_order` tool) |
| 10 | Admin: block `/mark_ready` on unpaid orders | User request | Done |
| 11 | Admin: accept `order_name` OR `order_id` in commands | User request | Done |
| 12 | Flask keep-alive thread for Render free-tier | User request | Done |
| 13 | Anti-hallucination architecture | User request | Done (see Section 4) |

---

## 3. Architecture

### 3.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    TELEGRAM                             │
│                                                         │
│  Customer Chat ◄─────► bot/handlers.py                  │
│  Admin Commands ◄────► owner/admin_handlers.py          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │    llm/agent.py      │
              │  (SYSTEM_PROMPT +    │
              │   LLM Tool Loop)     │
              └──────────┬───────────┘
                         │  OpenAI Function Calling
                         ▼
              ┌──────────────────────┐
              │    llm/tools.py      │
              │  (10 tool schemas +  │
              │   10 executors)      │
              │  + _find_item()      │
              └────┬─────────┬───────┘
                   │         │
          ┌────────▼───┐  ┌──▼───────────┐
          │ sessions/  │  │  database/   │
          │ cache.py   │  │  db.py       │
          │ (RAM)      │  │  menu_model  │
          │ Draft Cart │  │  order_model │
          │ History    │  │  (SQLite)    │
          └────────────┘  └──────────────┘
                              │
                         ┌────▼────────┐
                         │ services/   │
                         │ payos_svc   │
                         │ (Payment)   │
                         └─────────────┘
```

### 3.2 Data Flow: Order Lifecycle

```
  DRAFT (RAM)          PENDING (SQLite)         PAID (SQLite)          READY
  ───────────          ────────────────         ──────────────         ──────
  add_to_cart    ──►   finalize_draft   ──►     PayOS Polling   ──►   /mark_ready
  remove_from_cart     modify_pending           (auto-detect)         (admin only)
                       transfer_item
                       cancel_pending
                       update_order_info
```

### 3.3 Tool Registry (10 Tools)

| Tool | Phase | Purpose |
|---|---|---|
| `get_menu` | DRAFT | Fetch menu from SQLite |
| `add_to_cart` | DRAFT | Add item to RAM cart |
| `remove_from_cart` | DRAFT | Remove item from RAM cart |
| `finalize_draft_order` | DRAFT → PENDING | Save RAM cart to SQLite |
| `check_user_orders` | PENDING/PAID | List user's orders from DB |
| `modify_pending_order` | PENDING | Add/remove items in DB order |
| `transfer_item` | PENDING | Move item between two DB orders |
| `update_order_info` | PENDING/PAID | Change recipient or delivery time |
| `cancel_pending_order` | PENDING | Delete entire order from DB |
| `check_preparation_status` | PAID | Check if kitchen marked READY |

---

## 4. Problems Encountered & Solutions

### 4.1 LLM Hallucination — Item ID Fabrication

**Problem:** The LLM was given tool schemas with `item_id: integer`. When the user said "Bột Trà Xanh", the LLM would guess `item_id: 1` or `item_id: 27` from memory — often incorrectly. This caused:
- Wrong items being added to carts
- Failed deletions (LLM guessed wrong ID)
- Silent data corruption

**Solution:** Migrated ALL tool schemas from `item_id` (integer) to `item_name` (string). Created the `_find_item()` resolver in Python that accepts Vietnamese text and resolves it to the correct database record. The LLM now passes `"Bột Trà Xanh"` directly — Python handles the lookup.

**Impact:** Eliminated the #1 source of order corruption.

---

### 4.2 Substring Ambiguity in `_find_item()`

**Problem:** The menu contains items where one name is a substring of another:
- "Trân Châu Đen" (topping, 5,000đ) is a substring of "**Trà Sữa** Trân Châu Đen" (drink, 45,000đ)

The original `_find_item()` used `next(i for i if query in name)` — a sequential scan that always matched the longer name first, causing:
- Customer orders "Trân Châu Đen" → gets charged 45,000đ instead of 5,000đ
- "Swapping" items didn't change the total because both remove and add resolved to the same wrong item

**Solution:** Rewrote `_find_item()` with a **2-tier resolution strategy**:
1. **Exact match first** — `name.lower() == query.lower()`
2. **Shortest substring match** — among all candidates, pick the one with the shortest name (closest semantic match)

**Verified:** `"Trân Châu Đen"` → ID 20 (5,000đ) , `"Trà Sữa Trân Châu Đen"` → ID 1 (45,000đ) 

---

### 4.3 Ghost Memory — Stale Conversation History

**Problem:** When a customer deleted all orders and started a "new chat" on Telegram, the Python process kept old conversation history in `_user_sessions[user_id]["history"]`. The LLM read these stale messages and said things like "em đang có món tương tự rồi" about orders that no longer existed.

**Solution:**
1. `/start` command now calls `cache.clear_history()` + `cache.clear_cart()` — full memory wipe
2. History cap reduced from 20 → 10 messages
3. Added **NGUYÊN TẮC CHỐNG ẢO GIÁC** to the system prompt forbidding the LLM from using memory for order state

---

### 4.4 Premature QR Code Generation

**Problem:** The LLM would rush through the order flow:
1. Customer adds items → LLM immediately asks for name
2. Customer gives name → LLM immediately generates QR code

This was problematic because PENDING orders aren't finalized yet — items can still be moved/deleted.

**Solution:** Strict 3-phase protocol enforced in SYSTEM_PROMPT:
1. **DRAFT phase** — LLM adds items, waits for customer to say "Chốt đơn"
2. **Finalize phase** — LLM asks for name + time, calls `finalize_draft_order`, tells customer "chưa thanh toán"
3. **Payment phase** — Only when customer explicitly says "Tính tiền", LLM outputs `[CHECKOUT_ORDER] X`

---

### 4.5 Quantity Blindness

**Problem:** When a customer said "Cho 1 ly Bột Trà Xanh size M", the LLM would add the item but ignore the quantity — defaulting to asking "bao nhiêu ly?" even though the customer already said "1".

**Solution:** Updated `SYSTEM_PROMPT` to specify: "Mặc định số lượng là 1 nếu khách nói 'Cho 1 ly...'". Only ask for quantity if the customer genuinely didn't specify (e.g., "Cho em Trà xanh").

---

### 4.6 Dictionary Mutation Bug

**Problem:** `execute_add_to_cart()` was mutating the global menu dictionary by assigning `item_dict["size"] = size`. This polluted the cached menu data for subsequent lookups.

**Solution:** Always use `item_dict.copy()` before attaching the `size` attribute. Same fix applied to `execute_modify_pending_order()`.

---

### 4.7 Admin Marking Unpaid Orders as READY

**Problem:** The admin could type `/mark_ready 1` on a PENDING (unpaid) order, which made no logical sense — you can't prepare an order that hasn't been paid for.

**Solution:** Added validation in `admin_handlers.py`:
```python
if order['status'] != 'PAID':
    return "Đơn hàng đang ở trạng thái PENDING. Không thể đánh dấu READY!"
```

---

### 4.8 Schema-Backend Desync

**Problem:** After migrating tools to `item_name`, the `add_to_cart` schema was accidentally left with the old `item_id: integer` definition. The LLM read the schema and sent `{"item_id": 27}`, but the Python backend expected `item_name`. The backend received `None`, causing silent failures.

**Solution:** Audited all 10 tool schemas to ensure every `item_id` reference was replaced with `item_name`. This is a general lesson: **when changing a tool interface, both the schema AND the executor must be updated atomically**.

---

### 4.9 Cross-User Context Safety

**Concern raised:** "If many people chat simultaneously, can the bot mix up user A's data with user B's?"

**Analysis:** The architecture is **already safe**:
- `_user_sessions` is keyed by `customer_tg_id` (unique Telegram user ID)
- `process_user_message(customer_tg_id, text)` always passes the correct ID
- The LLM context is rebuilt from scratch per user per turn
- SQLite queries always filter by `customer_tg_id`

The only risk was per-user stale history, which was fixed in 4.3.

---

## 5. Full Implementation Timeline

### Phase 1 — Foundation
- Extracted menu from `menu.pdf` using PyPDF2, seeded into SQLite
- Built core Telegram bot with `/start` and message handler
- Integrated LiteLLM → GPT-4o-mini with basic system prompt
- Implemented `get_menu` and `add_to_cart` tools
- Created `payos_service.py` for QR payment links
- Added 15-second payment polling job

### Phase 2 — Multi-Order Management (Issue_EN.txt)
- Added `recipient_name`, `delivery_time`, `preparation_status` columns to orders table
- Implemented global `AUTOINCREMENT` order IDs with `order_name = {user_id}_{order_id}`
- Created Draft/PENDING/PAID lifecycle separation
- Built `finalize_draft_order`, `modify_pending_order`, `transfer_item`, `update_order_info` tools
- Reformatted `/view_orders` for human-readable admin display
- Added `/mark_ready`, `/delete_order`, `/delete_all_paid`, `/delete_all_pending` commands

### Phase 3 — Anti-Hallucination Architecture
- Migrated all tool schemas from `item_id: integer` to `item_name: string`
- Created `_find_item()` with exact-match-first + shortest-substring resolution
- Added `cancel_pending_order` tool
- Fixed dictionary mutation bugs (`.copy()`)
- Decoupled checkout from finalization (3-phase protocol)
- Enforced quantity elicitation rules

### Phase 4 — Session & Memory Hardening
- Added `clear_history()` to session cache
- Wired `/start` to reset history + cart
- Reduced history cap from 20 → 10
- Added **NGUYÊN TẮC CHỐNG ẢO GIÁC** to system prompt
- Refined prompt to separate "finalize DRAFT" from "checkout PENDING"

### Phase 5 — Production Preparation
- Added Flask keep-alive thread for Render free-tier
- Audited all project files, identified and removed debug artifacts
- Updated `requirements.txt` with all 6 dependencies (added `openai` and `flask`)
- Created test suites in `test_case/` for regression verification

---

## 6. Current System Limitations & Future Work

| Area | Limitation | Potential Improvement |
|---|---|---|
| **Payment Verification** | Uses 15s polling (can miss real-time events) | Implement a PayOS Webhook endpoint on the Flask server |
| **Menu Updates** | Admin adds items via `/add_item` command (manual) | Build a menu import tool from PDF/Excel |
| **Persistence** | Session history is in RAM (lost on restart) | Store conversation history in SQLite or Redis |
| **LLM Model** | GPT-4o-mini occasionally struggles with complex multi-step operations | Evaluate GPT-4o or fine-tuned model for better tool-call accuracy |
| **Persona** | SKILL.md specifies "Mẹ/Cô" but code uses "Chị" | Align SKILL.md with actual persona or make it configurable |
| **Upselling** | SKILL.md mentions upsell techniques | Not yet implemented — LLM could suggest toppings or combo deals |
| **Database** | SQLite is single-writer, may bottleneck under load | Migrate to PostgreSQL for production scale |

---

## 7. Final Project Structure

```
mama-ai-tea-shop-bot-developer/
├── SKILL.md                              # Project specification
├── menu/menu.pdf                         # Source menu reference
└── project-code/
    ├── main.py                           # Entry point (Telegram + Flask)
    ├── config.py                         # Env config loader
    ├── requirements.txt                  # All 6 pip dependencies
    ├── Dockerfile / Procfile             # Render deployment
    ├── tea_shop.db                       # SQLite database
    ├── bot/handlers.py                   # Customer: /start + LLM router
    ├── llm/agent.py                      # System prompt + tool loop
    ├── llm/tools.py                      # 10 tool schemas + executors
    ├── database/db.py                    # SQLite init + connection
    ├── database/menu_model.py            # Menu CRUD
    ├── database/order_model.py           # Order CRUD
    ├── owner/admin_handlers.py           # Admin commands (7 handlers)
    ├── services/payos_service.py         # PayOS integration
    ├── sessions/cache.py                 # RAM: draft cart + history
    └── test_case/                        # Regression test traces
```

---

*End of Analysis Report*
