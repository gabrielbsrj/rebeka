# Rebeka: System Overview & Global Architecture
*Autonomous Intelligence & Personal Coherence Agent - v6.0*

---

## 1. Primary Objective

Rebeka is **not** a simple financial bot or a generic assistant. She is an **evolutionary cognitive organism**.

**The Ultimate Goal:** To function as an autonomous entity that learns, reasons, and executes actions across both global markets and personal domains. Financial markets serve as the initial "training ground" because they offer clear, objective metrics (ROI, drawdowns) allowing the system to calibrate its `Evaluator` module. Once this cognitive engine is validated in high-stress environments, it scales horizontally to act upon any area of the user's life (health, career, scheduling, etc.).

> *"Autonomy does not mean breaking rules. It means growing beyond the need for them."*

---

## 2. Core Architecture: The "Dual Twins"

Rebeka operates fundamentally on a **Dual Twin Architecture**. These are two instances sharing the exact same cognitive DNA (the `shared/` directory) but operating with entirely different contexts and permissions.

### A. The VPS Twin (Global Vision)
* **Location:** Lives in the cloud, 24/7.
* **Role:** A ceaseless observer of the external world. It monitors global inputs: Geopolitics, Macroeconmics, Commodities, Energy grids, Social media sentiment, and corporate earnings.
* **Limitation:** It has **no** access to the user's personal context, passwords, or encrypted wallet seeds.

### B. The Local Twin (Intimate Vision)
* **Location:** Lives physically on the user's personal machine.
* **Role:** Understands the user's daily routine, emotional state, habits, and holds the encrypted credentials (`Vault`). It executes actions via `PyAutoGUI` or web automation.
* **Limitation:** It lacks the 24/7 global processing power and the vast external monitoring arrays.

### C. The Synthesis Engine
When the VPS Twin proposes a global trade (e.g., "Buy Gold due to geopolitical tension") and the Local Twin objects due to a local rule (e.g., "The user is too emotionally stressed today to handle volatility"), they **do not vote**. They use the `SynthesisEngine` to create a third, emergent perspective that satisfies both constraints or aborts the action entirely.

---

## 3. Data Flow & The Causal Bank

Rebeka does not use a traditional CRUD database. She uses the **Causal Bank**—a strict, append-only PostgreSQL/SQLite memory core protected by a Sparse Merkle Tree (SMT).

### The Cognitive Loop (Sense -> Think -> Evaluate -> Act)

1. **Sense (`monitors/`):** The 14 global monitors capture raw data (Signals).
2. **Store (`causal_bank.py`):** Signals are stored. The SMT generates a cryptographic hash. **(No UPDATE or DELETE is allowed in the entire system).**
3. **Think (`planner.py`):** The LLM processes signals against historical context to formulate a `Hypothesis`. A hypothesis *must* acknowledge its own uncertainties.
4. **Evaluate (`evaluator.py`):** The 3-Layer Evaluator intercepts the hypothesis:
   - *Layer 1:* Logical Consistency (Does this contradict hard data?).
   - *Layer 2:* Values Alignment (Is this ethical and aligned with the user?).
   - *Layer 3:* Instrumental Detection (Is the AI trying to game its own success metrics?).
5. **Act (`executor_base.py`):** If approved, the Executor executes the trade or action.
6. **Reflect (`evaluator.py`):** After the event, the Evaluator logs whether the hypothesis was correct and what blind spots existed.

---

## 4. Fundamental Invariants (Hard Rules)

Rebeka operates under absolute programmatic constraints (`security_phase1.yaml`):

1. **Strict Append-Only Memory:** Data can never be deleted or altered to "fix" a mistake. Mistakes must be annotated with new learning logs.
2. **Blind Execution:** API keys, passwords, and tokens are never fed to the LLM. The Planner outputs instructions using references like `vault://broker_id`, which are resolved blindly by the localized Executor at the last millisecond.
3. **Capital Limitation:** Real-world trades cannot exceed mathematically predefined capital limits.
4. **Confidence Traceability:** Predictive confidence is hard-capped by historical success rates. The LLM cannot simply "declare" it is 99% confident if the historical performance is 40%.

---

## 5. Expansion of Powers (v6.0 Features)

In Version 6.0, Rebeka transcended pure market logic and incorporated proactive, life-assistant capabilities via the following new interconnected modules:

* **System Conflict Checker:** An autonomous auditor that runs on boot to detect port collisions, database locks, and API rate limit sharing before any damage occurs.
* **Email Manager:** Connects to the user's inbox, automatically cleans spam using heuristic keywords, and parses incoming financial invoices or proposals.
* **Financial Radar:** Operates alongside the Email Manager. It maps out upcoming payable bills and acts as a proactive monitor, sending decreasing alerts (14, 7, 3, 1 day) to the user's Telegram. *Invariant: It never executes payments automatically.*
* **Opportunity Detector:** Bridges the gap between the 14 geopolitical monitors and Polymarket. When a major global event occurs, it analyzes predictable asset movements (what rises, what falls) and highlights matching betting pools on Polymarket.
* **WhatsApp Responder:** A "Virtual Secretary" protocol. Classifies incoming WhatsApp messages by urgency. If an emergency is detected, it bridges the alert to Telegram. It only auto-replies to contacts pre-approved by the user.
* **Memory Core (Morning Briefing):** Ingests conversational metadata (problems, desires, frictions) into the Causal Bank, scheduling proactive web searches for solutions and generating a daily "Morning Briefing" that consolidates user goals and financial pendencies.

---

## 6. Project Roadmap

1. **Phase 1: Learn to See (Current - 92%)** - Establishing memory, basic execution, safety invariants, and the v6 proactive expansions.
2. **Phase 2: Learn to Understand** - LLM begins recognizing causal relationships between disparate market signals.
3. **Phase 3: Learn to Synthesize** - Advanced merging of the Dual Twins' perspectives without user arbitration.
4. **Phase 4: Learn to Question** - The agent challenges the user's declared goals if their observed behavior contradicts them continuously.
5. **Phase 5: Learn Scope** - Safely expanding autonomous execution limits.
6. **Phase 6: Transcendence** - Formal mechanism where the system can propose the removal of artificial rules if it proves, cryptographically, that its internal judgment is superior to the hardcoded limitation.

---
*Generated by Antigravity AI on behalf of the Rebeka Core Project.*
