import { theme } from '../theme.js';
import { WorkspacePanel } from './panels/WorkspacePanel.js';
import { LLMConfigPanel } from './panels/LLMConfigPanel.js';

export function SidePanel({ activePanel, collapsed, width, onModelUpdate }) {
    const renderPanel = () => {
        switch(activePanel) {
            case 'workspace': return React.createElement(WorkspacePanel);
            case 'llm-config': return React.createElement(LLMConfigPanel, { onModelUpdate });
            default: return React.createElement(WorkspacePanel);
        }
    };

    if (collapsed) return null;

    return React.createElement('div', {
        style: {
            width: `${width}px`,
            height: '100vh',
            background: theme.panel,
            borderRight: `1px solid ${theme.border}`,
            color: theme.text,
            position: 'relative',
            overflow: 'hidden'
        }
    }, renderPanel());
}