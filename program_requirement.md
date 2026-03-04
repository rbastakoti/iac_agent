# Requirements Specification: Agentic IaC Workspace

## 1. Project Vision
A local-first, "Jupyter-style" intelligent workspace for Infrastructure as Code (IaC). The tool allows developers to manage, design, and visualize cloud environments using natural language through a side-by-side conversational terminal and a real-time resource graph.

---

## 2. Core Functional Requirements

### 2.1 Multi-LLM Orchestration
* **Provider Flexibility:** Support for OpenAI, Anthropic (Claude), Google (Gemini), and local models via Ollama or custom OpenAI-compatible endpoints like azure open ai models.
* **Inference Configuration:** A dedicated settings menu to manage API keys and model selection.
* **Domain Expertise:** The agent is specialized in Terraform HCL, cloud architecture patterns, and AWS/Azure/GCP providers.

### 2.2 Self-Managed Environment (NEW)
* **Automatic Dependency Injection:** Upon the first launch, the app must detect if required binaries (`terraform`, `az`, `aztfexport`) are installed.
* **Silent Installation:** If missing, the app should offer to download and install the correct versions for the user's OS (Windows/Mac/Linux) into a local `bin/` folder within the app directory to avoid messing with system-wide settings.
* **Version Management:** The app should ensure the installed versions are compatible with the agent's reasoning engine.

### 2.3 State-Based Agent Memory (Persistence) (NEW)
* **Logic Checkpointing:** Uses a state-machine (e.g., LangGraph) to save the agent's complete technical state—including variables, the current step in the workflow, and parsed Terraform metadata—to a local SQLite database.
* **Real-Time Resumption:** If the app is closed, the agent resumes exactly at the last node (e.g., waiting for confirmation) with all "Ghost Nodes" intact on the graph without needing to re-parse the entire conversation history.
* **Human-in-the-Loop "Wait" States:** The agent can remain in a "paused" state for extended periods while waiting for human input, maintaining full context of the pending deployment.

### 2.4 Infrastructure Discovery & Reverse Engineering (NEW)
* **Azure Resource Group Export:** Ability to target an existing Azure Resource Group and reverse-engineer it into Terraform code.
* **Tool Integration:** Integration with `aztfexport` (Azure Export for Terraform) to automate the discovery of existing cloud assets.
* **Auto-Ingestion:** Once exported, the generated `.tf` and `.tfstate` files must automatically populate the workspace and the visual graph.

### 2.5 Infrastructure Awareness
* **State Ingestion:** Automatic detection and parsing of local `terraform.tfstate` files.
* **Contextual Reasoning:** The agent analyzes existing resources to suggest modifications rather than redundant recreations.
* **Secret Scrubbing:** Local pre-processing to redact passwords and sensitive keys from state metadata before sending it to an LLM.

### 2.6 Interactive Interface (Split-Pane)
* **Conversational Console (Left):** An Xterm.js-powered terminal for chatting with the AI and viewing live `terraform plan/apply` logs.
* **Dynamic Resource Graph (Right):** A React Flow canvas that renders infrastructure connections.
* **Visual Diffing:** * **Solid Nodes:** Existing resources.
    * **Ghost/Dashed Nodes:** Proposed changes discussed in chat.
    * **Color Coding:** Green for additions, Red for deletions, Yellow for modifications.

---

## 3. Technical Stack
* **Backend:** Python (FastAPI) for local file system access and Terraform execution.
* **Frontend:** React + Tailwind CSS + React Flow.
* **Communication:** WebSockets for real-time synchronization between the terminal and the graph.
* **Tooling:** Direct integration with the Terraform CLI.

---

## 4. Operational Workflow (Conversational HITL)
The agent operates in a **Human-in-the-Loop (HITL)** loop, ensuring no destructive actions occur without manual confirmation.

1. **Discovery Dialogue:** User enters an Azure request (e.g., "Import my production RG"). The agent explains the steps and asks for permissions before running `aztfexport`.
2. **Consultative Design:** User discusses changes. The agent offers advice (e.g., "I recommend using a private subnet for the database") and updates the **Graph UI** with "Ghost" nodes as the conversation progresses.
3. **Drafting & Review:** Once a design is finalized, the agent generates the Terraform code and summarizes it in plain English. It asks: *"I've drafted the configuration. Shall I generate a plan to see the exact cloud impact?"*.
4. **Safety Plan Gate:** Agent executes `terraform plan` and provides a summary (e.g., "This will create 2 resources and cost ~$15/month"). It pauses for user review.
5. **Execution Confirmation:** The agent specifically waits for a confirmation phrase (e.g., "Proceed" or "Apply") before executing `terraform apply`. Destructive changes require an extra verification step.
---

## 5. Educational & Export Features
* **Architectural Explainer:** Tooltips on graph nodes explaining what the resource does.
* **Visual Export:** Export the live architecture as **SVG**, **PNG**, or **Mermaid.js** code for documentation.

## Decisions
- **Jupyter-style Architecture**: Local CLI server + web UI instead of desktop app
- **Single Workspace**: Simplified state management with one active workspace  
- **Scale Optimization**: Target 100 resources max for MVP performance