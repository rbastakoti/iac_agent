import { theme } from '../theme.js';

const { useState } = React;

export function ResizableQuadPane({ children, sidebarWidth }) {
    const [panelSizes, setPanelSizes] = useState({
        leftWidth: 50,
        rightWidth: 50,
        topHeight: 50,
        bottomHeight: 50
    });
    
    const mainWorkspaceWidth = `calc(100vw - 48px - ${sidebarWidth}px)`;
    
    return React.createElement('div', {
        style: {
            display: 'grid',
            gridTemplateColumns: `${panelSizes.leftWidth}% ${100 - panelSizes.leftWidth}%`,
            gridTemplateRows: `${panelSizes.topHeight}% ${100 - panelSizes.topHeight}%`,
            width: mainWorkspaceWidth,
            height: '100vh',
            gap: '1px',
            background: theme.border
        }
    }, [
        React.createElement('div', { key: 'top-left', style: { background: theme.background } }, children[0]),
        React.createElement('div', { key: 'top-right', style: { background: theme.background } }, children[1]),
        React.createElement('div', { key: 'bottom-left', style: { background: theme.background } }, children[2]),
        React.createElement('div', { key: 'bottom-right', style: { background: theme.background } }, children[3])
    ]);
}