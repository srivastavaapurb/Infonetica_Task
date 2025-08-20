## DS Intern Challenge: Two-Agent Prompt Adherence & Evaluation

This project simulates multi-turn conversations between two bots:

- Agent A: Customer service bot under test (prompt versions v0, v1, v2)
- Agent J: Proctor bot that drives the conversation and evaluates adherence

It runs ~N conversations, logs turns with latency and tags, computes per-conversation matrices and overall metrics, identifies failure modes, and demonstrates prompt improvements.

---

## Overview

FlowCrafter empowers clients to:

- Design flow blueprints using customizable phases and transitions  
- Launch live flow executions from saved blueprints  
- Perform actions that transition between phases, with rule enforcement  
- Inspect and list blueprints, executions, and all related metadata  

---

## Architecture

### Core Entities

- **BlueprintModel**: Defines the structure of a flow — phases and triggers  
- **ExecutionTracker**: Represents a running instance of a flow  
- **PhaseState**: A step in the flow (e.g., Draft, Review, Approved)  
- **FlowTrigger**: Defines transitions from one phase to another  

---

### Core Services

- **FlowLogicEngine**: Contains the main business logic for operations  
- **BlueprintGuard**: Enforces rules and constraints on flow definitions  
- **StateVaultService**: Manages in-memory data with file-based persistence  

---

## API Endpoints

### Blueprint Management

- `POST /api/blueprints` – Create a new blueprint definition  
- `GET /api/blueprints` – Retrieve all blueprint models  
- `GET /api/blueprints/{id}` – Retrieve details of a specific blueprint  

### Execution Management

- `POST /api/executions` – Start a new instance from a blueprint  
- `GET /api/executions` – View all current executions  
- `GET /api/executions/{id}` – Inspect a specific execution  
- `GET /api/executions/{id}/status` – View the current state and transition log  
- `POST /api/executions/{id}/transition` – Perform a flow-triggered action  

### Health Monitoring

- `GET /health` – Returns service uptime and health status  

---

## Validation Rules

### Blueprint Validation

- Must have exactly one phase marked as initial (`isInitial = true`)  
- All phase and trigger identifiers must be unique  
- All transitions must reference existing and enabled phases  
- Each trigger must define at least one source (`fromState`)  

### Runtime Action Validation

- Trigger must exist in the source blueprint  
- Trigger must be active (`enabled = true`)  
- Current phase must be included in the trigger's `fromStates`  
- Final phase transitions are disallowed  
- Destination phase must be valid and active  

---

## Data Persistence

The system stores data in memory and automatically backs it up as JSON files in the `/Data` directory:

- Blueprint files: `model_{id}.json`  
- Execution trackers: `tracker_{id}.json`  

Files are loaded at startup and persisted on each update.

---

## Example Usage

### 1️⃣ Define a Simple Approval Flow

```json
POST /api/blueprints
{
  "name": "Approval Flow",
  "description": "A three-step approval process",
  "states": [
    { "id": "draft", "name": "Draft", "isInitial": true, "isFinal": false, "enabled": true },
    { "id": "pending", "name": "Pending", "isInitial": false, "isFinal": false, "enabled": true },
    { "id": "approved", "name": "Approved", "isInitial": false, "isFinal": true, "enabled": true },
    { "id": "rejected", "name": "Rejected", "isInitial": false, "isFinal": true, "enabled": true }
  ],
  "actions": [
    { "id": "submit", "name": "Submit", "enabled": true, "fromStates": ["draft"], "toState": "pending" },
    { "id": "approve", "name": "Approve", "enabled": true, "fromStates": ["pending"], "toState": "approved" },
    { "id": "reject", "name": "Reject", "enabled": true, "fromStates": ["pending"], "toState": "rejected" }
  ]
}
````

### 2️⃣ Start a Flow Execution

```json
POST /api/executions
{
  "blueprintId": "{your-blueprint-id}"
}
```

### 3️⃣ Execute an Action

```json
POST /api/executions/{execution-id}/transition
{
  "actionId": "submit"
}
```

---

## Setup

1) Python 3.10+
2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Configure environment by copying `.env.example` to `.env` and filling values:

```env
AZURE_OPENAI_ENDPOINT=https://reasearch-interns.openai.azure.com
AZURE_OPENAI_API_KEY=YOUR_KEY
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
AZURE_OPENAI_API_VERSION=2025-01-01-preview
REQUEST_TIMEOUT_SECONDS=60
```

The client matches the provided curl with path `/openai/deployments/{deployment}/chat/completions?api-version=...`.

---

## Design Considerations

* **Hybrid Persistence**: Uses memory for speed, JSON for fault tolerance
* **Low Overhead**: Minimal dependencies (ASP.NET Core, Swagger, Newtonsoft.Json)
* **Strict Validations**: Protects flow consistency during definition and runtime
* **Audit Trails**: Maintains full execution history of transitions
* **Standard REST API**: Easy to integrate and extend
* **Developer-Friendly**: Swagger for interactive API documentation

---

## Run Simulations

Run v0 (flawed prompt):

```bash
python run_simulation.py --version v0 --n 20 --max_turns 8 --out runs
```

Run improved prompts:

```bash
python run_simulation.py --version v1 --n 20 --max_turns 8 --out runs
python run_simulation.py --version v2 --n 20 --max_turns 8 --out runs
```

Outputs are saved under `runs/<version>/`:

- Per-conversation JSON logs (turns with latency and tags)
- `summary.csv` per version
- Run metadata with aggregate metrics and top failure modes

## Colab/Notebook

Open `notebooks/DS_Intern_Challenge.ipynb` to run experiments for v0→v1→v2 and visualize metrics.

---
