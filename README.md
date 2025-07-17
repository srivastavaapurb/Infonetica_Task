

### 📄 `README.md`

````markdown
# FlowCrafter API

A lightweight backend service to define, manage, and execute configurable flow-based task engines with robust validation and state control.

---

## 🌐 Overview

FlowCrafter allows clients to:

1. **Design** custom state blueprints with configurable phases and triggers
2. **Launch** runtime executions from those blueprints
3. **Perform** actions to transition between states under strict validation
4. **Query** the structure and status of blueprints and executions

---

## 🧱 Core Concepts

- **BlueprintModel**: A template containing phases (states) and triggers (actions)
- **ExecutionTracker**: A live instance of a blueprint, tracking progress and history
- **PhaseState**: Represents a step within a blueprint (e.g., draft, review, complete)
- **FlowTrigger**: A rule-driven transition between two phase states

---

## 🛠️ Services

- **FlowLogicEngine**: Core business rules and flow execution logic
- **BlueprintGuard**: Ensures validity and consistency of blueprints and transitions
- **StateVaultService**: In-memory + JSON persistence engine

---

## 🔌 API Endpoints

### 🔧 Blueprint Management

- `POST /api/blueprints` – Create a new blueprint template
- `GET /api/blueprints` – List all saved blueprint models
- `GET /api/blueprints/{id}` – Fetch details of a specific blueprint

### 🚀 Execution Runners

- `POST /api/executions` – Instantiate a blueprint into an execution tracker
- `GET /api/executions` – View all live execution trackers
- `GET /api/executions/{id}` – View a specific execution
- `GET /api/executions/{id}/status` – Inspect current state and log
- `POST /api/executions/{id}/transition` – Execute a trigger (action)

### ❤️‍🩹 Health Check

- `GET /health` – System status check

---

## ✅ Validation Rules

### Blueprint Integrity

- Only one `isInitial: true` state is allowed
- Unique IDs for all phases and triggers
- All transitions must point to existing, enabled phase states
- Triggers must include at least one `fromState`

### Runtime Validations

- Trigger must exist and be enabled
- Current state must match one of the allowed `fromStates`
- Transitions from final states are disallowed
- Destination phase must be valid and enabled

---

## 💾 Persistence Layer

FlowCrafter uses in-memory data structures with file-based backups under `/Data`:

- Blueprints: `model_{id}.json`
- Executions: `tracker_{id}.json`

---

## 🧪 Example Usage

### 1. Define an Approval Flow

```json
POST /api/blueprints
{
  "name": "Doc Approval Flow",
  "description": "Three-step approval process",
  "states": [
    { "id": "draft", "name": "Draft", "isInitial": true, "isFinal": false, "enabled": true },
    { "id": "pending", "name": "Awaiting Review", "isInitial": false, "isFinal": false, "enabled": true },
    { "id": "approved", "name": "Approved", "isFinal": true, "enabled": true }
  ],
  "actions": [
    { "id": "send", "name": "Send for Review", "enabled": true, "fromStates": ["draft"], "toState": "pending" },
    { "id": "approve", "name": "Approve", "enabled": true, "fromStates": ["pending"], "toState": "approved" }
  ]
}
````

### 2. Start Execution

```json
POST /api/executions
{
  "blueprintId": "{blueprint-guid}"
}
```

### 3. Perform Action

```json
POST /api/executions/{execution-id}/transition
{
  "actionId": "send"
}
```

---

## 🚀 Run Locally

### Requirements

* .NET 8 SDK

### Development Mode

```bash
cd FlowCrafter
dotnet run
```

The Swagger UI will be available at `https://localhost:7xxx`

### Build

```bash
dotnet build
```

---

## ⚙️ Design Rationale

* **Memory-first Persistence** with file backup for small teams or POCs
* **Simple API Surface** using REST
* **Declarative Validation** for safe flows
* **Trackable Transitions** through complete audit trail
* **OpenAPI/Swagger Docs** for easy testing

---

## 🔮 Future Ideas

* SQL/NoSQL persistence adapters
* Conditional triggers
* Versioned blueprint templates
* Role-based access for transitions
* Webhooks on state change
* Integration with message queues (RabbitMQ, Kafka)

---

```

---

Shall I now proceed with **Controllers** (`WorkflowDefinitionsController.cs`, `WorkflowInstancesController.cs`) and rewrite them with the new names and logic?
```
