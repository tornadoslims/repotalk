import { useEffect, useRef, useCallback } from 'react';
import cytoscape from 'cytoscape';
import fcose from 'cytoscape-fcose';
import { useGraphStore } from '@/stores/graphStore';
import { NODE_COLORS, EDGE_STYLES } from '@/lib/constants';
import { layouts } from '@/lib/graphLayout';
import { GraphControls } from './GraphControls';
import { GraphTooltip } from './GraphTooltip';
import { GraphLegend } from './GraphLegend';
import type { GraphNode } from '@/api/types';
import { useState } from 'react';

// Register fcose layout once
try { cytoscape.use(fcose); } catch { /* already registered */ }

export function GraphCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const { graphData, setSelectedNode, highlightedNodes, edgeFilters, layoutMode, searchQuery } = useGraphStore();
  const [tooltipNode, setTooltipNode] = useState<{ node: GraphNode; x: number; y: number } | null>(null);

  const nodes = graphData?.nodes || [];
  const edges = graphData?.edges || [];

  // Initialize cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            color: '#e2e8f0',
            'font-size': '11px',
            'text-valign': 'bottom',
            'text-margin-y': 8,
            width: 'data(size)',
            height: 'data(size)',
            'border-width': 2,
            'border-color': 'data(color)',
            'border-opacity': 0.3,
          },
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#8b5cf6',
            'border-opacity': 1,
          },
        },
        {
          selector: 'node.highlighted',
          style: {
            'border-width': 3,
            'border-color': '#f59e0b',
            'border-opacity': 1,
          },
        },
        {
          selector: 'node.dimmed',
          style: {
            opacity: 0.3,
          },
        },
        {
          selector: 'node.search-match',
          style: {
            'border-width': 3,
            'border-color': '#22c55e',
            'border-opacity': 1,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 'data(width)',
            'line-color': 'data(color)',
            'target-arrow-color': 'data(color)',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'line-style': 'solid' as const,
            opacity: 0.7,
          },
        },
        {
          selector: 'edge.highlighted',
          style: {
            opacity: 1,
            width: 3,
          },
        },
        {
          selector: 'edge.dimmed',
          style: {
            opacity: 0.15,
          },
        },
        {
          selector: 'edge.hidden',
          style: {
            display: 'none',
          },
        },
      ],
      elements: [],
      layout: { name: 'preset' },
      minZoom: 0.2,
      maxZoom: 4,
      wheelSensitivity: 0.3,
    });

    cyRef.current = cy;

    // Node click
    cy.on('tap', 'node', (evt) => {
      const nodeData = evt.target.data();
      setSelectedNode({
        id: nodeData.id,
        label: nodeData.label,
        type: nodeData.nodeType,
        summary: nodeData.summary,
      });
    });

    // Node hover - highlight connected
    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      const neighborhood = node.closedNeighborhood();
      cy.elements().addClass('dimmed');
      neighborhood.removeClass('dimmed');
      neighborhood.edges().addClass('highlighted');

      // Show tooltip
      const pos = node.renderedPosition();
      setTooltipNode({
        node: { id: node.data('id'), label: node.data('label'), type: node.data('nodeType'), summary: node.data('summary') },
        x: pos.x,
        y: pos.y,
      });
    });

    cy.on('mouseout', 'node', () => {
      cy.elements().removeClass('dimmed').removeClass('highlighted');
      setTooltipNode(null);
    });

    // Background click to deselect
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        setSelectedNode(null);
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  // Update elements when data changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.elements().remove();

    if (nodes.length === 0) return;

    const elements: cytoscape.ElementDefinition[] = [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          color: NODE_COLORS[n.type] || NODE_COLORS.external || '#6b7280',
          nodeType: n.type,
          summary: n.summary || '',
          size: n.type === 'file' ? 35 : n.type === 'class' ? 30 : n.type === 'module' ? 35 : 25,
        },
      })),
      ...edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          edgeType: e.type,
          color: EDGE_STYLES[e.type]?.color || '#6b7280',
          width: EDGE_STYLES[e.type]?.width || 1,
          lineStyle: EDGE_STYLES[e.type]?.style || 'solid',
        },
      })),
    ];

    cy.add(elements);

    const layoutConfig = layouts[layoutMode] || layouts.fcose;
    cy.layout(layoutConfig as cytoscape.LayoutOptions).run();
  }, [nodes, edges, layoutMode]);

  // Apply edge filters
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.edges().forEach((edge) => {
      const type = edge.data('edgeType');
      if (edgeFilters[type] === false) {
        edge.addClass('hidden');
      } else {
        edge.removeClass('hidden');
      }
    });
  }, [edgeFilters]);

  // Apply highlights
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass('highlighted');
    highlightedNodes.forEach((id) => {
      cy.getElementById(id).addClass('highlighted');
    });
  }, [highlightedNodes]);

  // Apply search
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass('search-match');
    if (searchQuery) {
      cy.nodes().forEach((node) => {
        if (node.data('label').toLowerCase().includes(searchQuery.toLowerCase())) {
          node.addClass('search-match');
        }
      });
    }
  }, [searchQuery]);

  const handleZoomIn = () => cyRef.current?.zoom(cyRef.current.zoom() * 1.3);
  const handleZoomOut = () => cyRef.current?.zoom(cyRef.current.zoom() / 1.3);
  const handleFit = () => cyRef.current?.fit(undefined, 50);

  return (
    <div className="relative w-full h-full bg-background">
      <div ref={containerRef} className="w-full h-full" />
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center text-muted-foreground text-sm">
          No graph data. Index the project to build the knowledge graph.
        </div>
      )}
      <GraphControls onZoomIn={handleZoomIn} onZoomOut={handleZoomOut} onFit={handleFit} />
      <GraphLegend />
      {tooltipNode && <GraphTooltip node={tooltipNode.node} x={tooltipNode.x} y={tooltipNode.y} />}
    </div>
  );
}
