# UI Specification: Agentic IaC VSCode-Style Workspace

## 1. Interface Philosophy
The interface is a high-density, professional environment designed to bridge the gap between AI automation and low-level infrastructure control. It utilizes a **VSCode-inspired layout** with a dedicated sidebar and **Quad-Pane** main workspace where every part of the deployment lifecycle—conversation, command execution, code generation, and visual topology—is visible simultaneously.

---

## 2. Layout Structure
The workspace is built on a single-page reactive layout using resizable panels with a **VSCode-style architecture**.

### 2.1 Overall Layout Structure
```
┌────────┬─────────────────────────────────────────────────┐
│        │                 Main Workspace                  │
│   S    ├────────────────────┬────────────────────────────┤
│   I    │   AI Conversation   │    HCL File Explorer       │
│   D    │   (Top-Left)       │    (Top-Right)             │
│   E    ├────────────────────┼────────────────────────────┤
│   B    │ Operational Terminal│    Resource Graph          │
│   A    │  (Bottom-Left)     │   (Bottom-Right)           │
│   R    │                    │                            │
└────────┴────────────────────┴────────────────────────────┘
```

### 2.2 VSCode-Style Sidebar (Left)
| Component | Name | Purpose | Key Features |
| :--- | :--- | :--- | :--- |
| **Activity Bar** | `ActivityBar` | Primary navigation | Settings, LLM Config, Workspace, Extensions icons |
| **Side Panel** | `SidePanel` | Context-sensitive content | Configuration forms, file tree, settings panels |

### 2.3 Main Workspace - Quad-Pane Grid
| Quadrant | Name | Component | Key Functional Requirement |
| :--- | :--- | :--- | :--- |
| **Top-Left** | **AI Conversation** | `ChatContainer` | Supports **token-by-token streaming** via WebSockets. |
| **Bottom-Left** | **Operational Terminal** | `XtermComponent` | Renders raw stdout/stderr from CLI (Terraform, Azure, Setup). |
| **Top-Right** | **HCL File Explorer** | `CodeViewer` | Real-time preview of `.tf` files with syntax highlighting. |
| **Bottom-Right** | **Resource Graph** | `ReactFlowCanvas` | Dynamic visualization of infrastructure and "Ghost Nodes." |



---

## 3. Sidebar Components (VSCode-Style)

### 3.1 Activity Bar (Far Left, 48px wide)
A vertical icon bar for primary navigation, similar to VSCode's activity bar:
* **Settings Icon** (⚙️): Access to general application settings
* **LLM Config Icon** (🤖): LLM provider configuration and API keys
* **Workspace Icon** (📁): Current workspace status and file management
* **Extensions Icon** (🧩): Future extensibility (plugins, custom tools)

### 3.2 Side Panel (Collapsible, 300px default width)
Context-sensitive panel that changes based on Activity Bar selection:

#### 3.2.1 Settings Panel (⚙️)
* **Application Preferences**
  - Theme selection (Dark/Light)
  - Auto-save settings
  - Terminal preferences
  - Graph layout options
* **Workspace Configuration**
  - Default workspace directory
  - File watchers (auto-detect .tf files)
  - Backup and restore preferences

#### 3.2.2 LLM Configuration Panel (🤖)
* **Provider Selection**
  - Dropdown: OpenAI, Anthropic (Claude), Google (Gemini), Ollama, Azure OpenAI
  - Custom endpoint configuration for OpenAI-compatible APIs
* **Authentication**
  - API Key input fields (masked)
  - Connection status indicators (🟢 Connected, 🔴 Invalid, 🟡 Testing)
  - Test connection button
* **Model Settings**
  - Model selection dropdown (based on provider)
  - Temperature and other parameters
  - Token limits and cost estimation
* **Advanced Options**
  - System prompt customization
  - Context window management
  - Response streaming preferences

#### 3.2.3 Workspace Panel (📁)
* **File Tree**
  - Current workspace files (.tf, .tfstate, etc.)
  - Quick file actions (open, delete, rename)
* **Workspace Status**
  - Terraform state summary
  - Last deployment status
  - Resource count and health checks

---

## 4. Main Workspace Component Details

## 4. Main Workspace Component Details

### 4.1 AI Conversation (Top-Left)
* **Streaming Logic:** Incoming messages must render immediately as chunks arrive to provide a "live thinking" experience.
* **Context Awareness:** Displays status indicators when the agent is "Analyzing State" or "Generating Plan."
* **Input Bar:** Supports multiline natural language queries.

### 4.2 Operational Terminal (Bottom-Left)
* **Xterm.js Integration:** A fully functional terminal emulator.
* **Visibility:** Each box has a dedicated slider to ensure terminal logs can be fully inspected even in high-density views.
* **Content:** Shows installation progress for Terraform/Azure CLI and raw deployment logs.

### 4.3 HCL File Explorer (Top-Right)
* **Real-Time Edits:** As the LLM drafts code, the explorer reflects these changes instantly.
* **File Tree:** Minimalist sidebar to switch between `main.tf`, `variables.tf`, and `outputs.tf`.
* **Sync:** Tied to the backend file system via WebSockets.

### 4.4 Resource Graph (Bottom-Right)
* **React Flow Engine:** Renders resources as interactive nodes.
* **Visual States:**
    * **Solid Nodes:** Existing resources confirmed in the cloud.
    * **Ghost/Dashed Nodes:** Proposed resources currently being discussed in chat.
    * **Color Logic:** Green (Create), Yellow (Modify), Red (Destroy).



---

## 5. Interaction & UX

### 5.1 Sidebar Behavior (VSCode-Style)
* **Collapsible:** The sidebar can be collapsed to provide more space for the main workspace
* **Activity Bar Always Visible:** The 48px activity bar remains visible even when sidebar is collapsed
* **Panel Switching:** Clicking activity bar icons switches the side panel content
* **Keyboard Shortcuts:** 
  - `Ctrl+Shift+E` for Workspace panel
  - `Ctrl+Shift+,` for Settings panel
  - `Ctrl+Shift+L` for LLM Config panel
* **State Persistence:** Sidebar width and active panel persisted in `localStorage`

### 5.2 Main Workspace - Resizable Panels
* The main workspace quadrants are separated by **draggable gutters**.
* Users can slide vertical or horizontal bars to focus on the Graph while shrinking the Code Explorer, or vice versa.
* Layout state (pane percentages) is persisted in `localStorage`.
* **Full-screen Mode:** Double-clicking any pane header maximizes that pane temporarily

### 5.3 Synchronization Engine
The frontend must maintain a unified state. When an LLM streams a suggestion:
1. The **Chat** shows the explanation.
2. The **HCL Explorer** shows the code block.
3. The **Graph** renders the ghost node.
*All three must update in parallel via the same backend state-change event.*

---

## 6. Technical Stack
* **Framework:** React (Vite)
* **Layout Manager:** `react-resizable-panels` for main workspace, custom components for sidebar
* **Styling:** Tailwind CSS (Dark Mode optimized, VSCode-inspired theme)
* **Icons:** `react-icons` or `lucide-react` for activity bar icons
* **Graphing:** `reactflow`
* **Terminal:** `xterm.js` + `xterm-addon-fit`
* **Communication:** WebSockets for bidirectional streaming and sync.

---

## 7. Development Phases
1. **Phase 1:** Implement the VSCode-style sidebar with activity bar and collapsible panels
2. **Phase 2:** Integrate LLM configuration forms and settings panels
3. **Phase 3:** Implement the resizable 4-box main workspace grid
4. **Phase 4:** Integrate Xterm.js and mock streaming chat
5. **Phase 5:** Connect React Flow with "Ghost Node" logic
6. **Phase 6:** Connect WebSocket handlers for real-time HCL Explorer updates
7. **Phase 7:** Polish interactions, keyboard shortcuts, and state persistence