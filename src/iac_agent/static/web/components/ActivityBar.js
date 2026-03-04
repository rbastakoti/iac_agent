import { theme } from '../theme.js';

export function ActivityBar({ activePanel, onPanelChange, sidebarCollapsed, onToggleSidebar }) {
    const activityItems = [
        { id: 'workspace', icon: '📁', title: 'Workspace' },
        { id: 'llm-config', icon: '⚙️', title: 'LLM Configuration' }
    ];

    return React.createElement('div', {
        style: {
            width: '48px',
            height: '100vh',
            background: theme.activityBar,
            borderRight: `1px solid ${theme.border}`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            paddingTop: '8px',
            zIndex: 100
        }
    }, [
        // Activity items
        ...activityItems.map(item =>
            React.createElement('button', {
                key: item.id,
                onClick: () => {
                    if (activePanel === item.id && !sidebarCollapsed) {
                        onToggleSidebar();
                    } else {
                        onPanelChange(item.id);
                        if (sidebarCollapsed) {
                            onToggleSidebar();
                        }
                    }
                },
                title: item.title,
                style: {
                    width: '40px',
                    height: '40px',
                    background: activePanel === item.id && !sidebarCollapsed ? theme.accent + '40' : 'transparent',
                    border: activePanel === item.id && !sidebarCollapsed ? `1px solid ${theme.accent}` : '1px solid transparent',
                    borderRadius: '4px',
                    color: theme.text,
                    cursor: 'pointer',
                    marginBottom: '4px',
                    fontSize: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s ease'
                },
                onMouseEnter: (e) => {
                    if (activePanel !== item.id) {
                        e.target.style.background = theme.hover;
                    }
                },
                onMouseLeave: (e) => {
                    if (activePanel !== item.id) {
                        e.target.style.background = 'transparent';
                    }
                }
            }, item.icon)
        ),
        
        // Spacer
        React.createElement('div', { key: 'spacer', style: { flex: 1 } }),
        
        // Collapse button
        React.createElement('button', {
            key: 'collapse',
            onClick: onToggleSidebar,
            title: sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar',
            style: {
                width: '40px',
                height: '40px',
                background: 'transparent',
                border: '1px solid transparent',
                borderRadius: '4px',
                color: theme.textMuted,
                cursor: 'pointer',
                marginBottom: '8px',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s ease'
            },
            onMouseEnter: (e) => e.target.style.background = theme.hover,
            onMouseLeave: (e) => e.target.style.background = 'transparent'
        }, sidebarCollapsed ? '▶' : '◀')
    ]);
}