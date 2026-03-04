import { theme } from '../../theme.js';

const { useState } = React;

export function ResourceGraph() {
    const [nodes] = useState([
        { id: 'rg', type: 'existing', label: 'Resource Group\nrg-dev-eastus', x: 80, y: 60 },
        { id: 'vnet', type: 'existing', label: 'Virtual Network\nvnet-dev\n10.0.0.0/16', x: 280, y: 60 },
        { id: 'subnet', type: 'ghost', label: 'Subnet (Proposed)\nsubnet-web\n10.0.1.0/24', x: 480, y: 60 },
        { id: 'vm', type: 'ghost', label: 'Virtual Machine (Proposed)\nvm-web-01\nStandard_B2s', x: 480, y: 180 },
        { id: 'nsg', type: 'ghost', label: 'Network Security Group\nnsg-web (Proposed)', x: 280, y: 180 }
    ]);
    
    const getNodeStyle = (nodeType) => {
        const base = {
            position: 'absolute',
            padding: '8px',
            borderRadius: '6px',
            fontSize: '10px',
            textAlign: 'center',
            whiteSpace: 'pre-line',
            minWidth: '100px',
            maxWidth: '140px',
            cursor: 'pointer',
            border: '2px solid'
        };
        
        if (nodeType === 'existing') {
            return {
                ...base,
                background: theme.success + '20',
                borderColor: theme.success,
                color: theme.text
            };
        } else {
            return {
                ...base,
                background: theme.warning + '20',
                borderColor: theme.warning,
                borderStyle: 'dashed',
                color: theme.text
            };
        }
    };
    
    return React.createElement('div', {
        style: {
            background: theme.background,
            height: '100%',
            position: 'relative'
        }
    }, [
        // Header
        React.createElement('div', {
            key: 'header',
            style: {
                padding: '8px 12px',
                borderBottom: `1px solid ${theme.border}`,
                background: theme.panel,
                color: theme.text,
                fontSize: '13px',
                fontWeight: '600',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
            }
        }, [
            React.createElement('span', { key: 'icon' }, '🌐'),
            'Infrastructure Graph',
            React.createElement('div', {
                key: 'legend',
                style: { marginLeft: 'auto', display: 'flex', gap: '12px', fontSize: '11px' }
            }, [
                React.createElement('span', {
                    key: 'existing',
                    style: { color: theme.success, display: 'flex', alignItems: 'center', gap: '4px' }
                }, ['●', 'Live']),
                React.createElement('span', {
                    key: 'proposed',
                    style: { color: theme.warning, display: 'flex', alignItems: 'center', gap: '4px' }
                }, ['⚬', 'Planned'])
            ])
        ]),
        
        // Graph canvas
        React.createElement('div', {
            key: 'canvas',
            style: {
                height: 'calc(100% - 40px)',
                position: 'relative',
                overflow: 'hidden',
                background: `linear-gradient(90deg, ${theme.border} 1px, transparent 1px), linear-gradient(${theme.border} 1px, transparent 1px)`,
                backgroundSize: '20px 20px'
            }
        }, [
            // Connection lines (simple implementation)
            React.createElement('svg', {
                key: 'connections',
                style: {
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    pointerEvents: 'none'
                }
            }, [
                React.createElement('line', {
                    key: 'rg-vnet',
                    x1: 150, y1: 95, x2: 280, y2: 95,
                    stroke: theme.success,
                    strokeWidth: 2
                }),
                React.createElement('line', {
                    key: 'vnet-subnet',
                    x1: 380, y1: 95, x2: 480, y2: 95,
                    stroke: theme.warning,
                    strokeWidth: 2,
                    strokeDasharray: '5,5'
                }),
                React.createElement('line', {
                    key: 'subnet-vm',
                    x1: 550, y1: 110, x2: 550, y2: 180,
                    stroke: theme.warning,
                    strokeWidth: 2,
                    strokeDasharray: '5,5'
                })
            ]),
            
            // Nodes
            ...nodes.map(node => 
                React.createElement('div', {
                    key: node.id,
                    style: {
                        ...getNodeStyle(node.type),
                        left: node.x,
                        top: node.y
                    },
                    title: `${node.type === 'ghost' ? 'Proposed: ' : 'Deployed: '}${node.label.split('\n')[0]}`
                }, node.label)
            )
        ])
    ]);
}