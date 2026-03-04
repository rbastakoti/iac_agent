// ================================================================================================
// IAC AGENT - AGENTIC INFRASTRUCTURE AS CODE WORKSPACE  
// VSCode-Style Interface with Multi-LLM Support (Modular Version)
// ================================================================================================

console.log('🚀 Starting IaC Agent VSCode-Style Workspace...');

// Import the main App component
import { App } from './components/App.js';

// ================================================================================================
// APPLICATION INITIALIZATION & RENDERING
// ================================================================================================

if (typeof React !== 'undefined' && typeof ReactDOM !== 'undefined') {
    console.log('Rendering IaC Agent App from modular components...');
    const container = document.getElementById('root');
    if (container) {
        const root = ReactDOM.createRoot(container);
        root.render(React.createElement(App));
        console.log('✅ VSCode-Style IaC Agent loaded successfully!');
    } else {
        console.error('Root container not found');
    }
} else {
    console.error('React not available');
    document.body.innerHTML = '<div style="padding:50px;background:red;color:white;">React libraries not loaded</div>';
}