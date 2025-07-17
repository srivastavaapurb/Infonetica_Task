# FlowCrafter API

FlowCrafter is a lightweight backend API built to handle custom flow-based state engines with configurable transitions, validations, and persistent state tracking.

---

## 🧭 Overview

FlowCrafter empowers clients to:

- 📐 Design flow blueprints using customizable phases and transitions  
- 🚀 Launch live flow executions from saved blueprints  
- 🔁 Perform actions that transition between phases, with rule enforcement  
- 🔎 Inspect and list blueprints, executions, and all related metadata  

---

## 🧱 Architecture

### 📦 Core Entities

- **BlueprintModel**: Defines the structure of a flow — phases and triggers  
- **ExecutionTracker**: Represents a running instance of a flow  
- **PhaseState**: A step in the flow (e.g., Draft, Review, Approved)  
- **FlowTrigger**: Defines transitions from one phase to another  

---

### 🔧 Core Services

- **FlowLogicEngine**: Contains the main business logic for operations  
- **BlueprintGuard**: Enforces rules and constraints on flow definitions  
- **StateVaultService**: Manages in-memory data with file-based persistence  

---

## 🌐 API Endpoints

### 🔷 Blueprint Management

- `POST /api/blueprints` – Create a new blueprint definition  
- `GET /api/blueprints` – Retrieve all blueprint models  
- `GET /api/blueprints/{id}` – Retrieve details of a specific blueprint  

### ⚙️ Execution Management

- `POST /api/executions` – Start a new instance from a blueprint  
- `GET /api/executions` – View all current executions  
- `GET /api/executions/{id}` – Inspect a specific execution  
- `GET /api/executions/{id}/status` – View the current state and transition log  
- `POST /api/executions/{id}/transition` – Perform a flow-triggered action  

### 🔍 Health Monitoring

- `GET /health` – Returns service uptime and health status  

---

## ✅ Validation Rules

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

## 💾 Data Persistence

The system stores data in memory and automatically backs it up as JSON files in the `/Data` directory:

- Blueprint files: `model_{id}.json`  
- Execution trackers: `tracker_{id}.json`  

Files are loaded at startup and persisted on each update.

---

## 🔁 Example Usage

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
