import { useEffect, useRef } from 'react';
import cytoscape from 'cytoscape';
import { Maximize2, Minus, Plus } from 'lucide-react';
import type { GraphResponse } from '@/types/api';
import { Button } from '@/components/ui/button';

const graphStyles: NonNullable<cytoscape.CytoscapeOptions['style']> = [
  {
    selector: 'node',
    style: {
      'background-color': '#94a3b8',
      label: '',
      color: '#334155',
      'font-size': 9,
      'font-weight': 'bold',
      'text-wrap': 'ellipsis',
      // Cytoscape's stylesheet typings model this value as a CSS length string.
      'text-max-width': '120px',
      'text-valign': 'bottom',
      'text-margin-y': 7,
      width: 15,
      height: 15,
      'border-width': 1,
      'border-color': '#ffffff',
      'border-opacity': 0.95,
      'overlay-opacity': 0,
    },
  },
  { selector: 'node[type="user"]', style: { 'background-color': '#2563eb', width: 27, height: 27 } },
  { selector: 'node[type="event"]', style: { 'background-color': '#64748b' } },
  { selector: 'node[type="evidence"]', style: { 'background-color': '#0f766e', width: 21, height: 21 } },
  { selector: 'node[type="anomaly"]', style: { 'background-color': '#ea580c', width: 23, height: 23 } },
  { selector: 'node[type="location"]', style: { 'background-color': '#7c3aed', width: 19, height: 19 } },
  { selector: 'node[type="document"]', style: { 'background-color': '#0891b2', width: 19, height: 19 } },
  {
    selector: 'node.hovered, node:selected',
    style: {
      label: 'data(label)',
      'font-size': 11,
      color: '#0f172a',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.94,
      'text-background-padding': '3px',
      'z-index': 999,
    },
  },
  {
    selector: 'edge',
    style: {
      width: 1,
      'line-color': '#cbd5e1',
      'target-arrow-color': '#94a3b8',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      opacity: 0.38,
      label: '',
    },
  },
  {
    selector: 'edge.hovered, edge:selected',
    style: {
      label: 'data(label)',
      'font-size': 8,
      color: '#475569',
      'text-rotation': 'autorotate',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.9,
      'text-background-padding': '2px',
      opacity: 0.9,
    },
  },
  { selector: '.dimmed', style: { opacity: 0.12 } },
  { selector: 'node:selected', style: { 'border-width': 3, 'border-color': '#1d4ed8', 'overlay-opacity': 0.08, 'overlay-color': '#2563eb' } },
  { selector: 'edge:selected', style: { width: 2.5, 'line-color': '#2563eb', 'target-arrow-color': '#2563eb', opacity: 1 } },
];

export function EvidenceGraph({
  data,
  onSelect,
}: {
  data: GraphResponse;
  onSelect: (node: Record<string, unknown>) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Use Cytoscape's explicit Core type. ReturnType<typeof cytoscape> can
  // resolve to the wrong overload when the package exposes multiple overloads.
  const cyRef = useRef<cytoscape.Core | null>(null);
  const elements = data.elements;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const cy = cytoscape({
      container,
      elements: [...elements.nodes, ...elements.edges],
      style: graphStyles,
      layout: {
        name: 'cose',
        animate: false,
        fit: true,
        padding: 48,
        nodeRepulsion: 14000,
        idealEdgeLength: 115,
        componentSpacing: 120,
        nodeOverlap: 28,
        numIter: 1000,
        gravity: 0.15,
      },
      minZoom: 0.15,
      maxZoom: 3,
      selectionType: 'single',
      boxSelectionEnabled: false,
    });
    cyRef.current = cy;

    cy.on('mouseover', 'node, edge', (event) => event.target.addClass('hovered'));
    cy.on('mouseout', 'node, edge', (event) => event.target.removeClass('hovered'));
    cy.on('tap', 'node', (event) => {
      const node = event.target;
      cy.elements().addClass('dimmed');
      node.closedNeighborhood().removeClass('dimmed');

      // toArray() retains Cytoscape's element typing and avoids an implicit-any
      // callback from the collection's overloaded map() signature.
      const connectedNodes = node
        .neighborhood('node')
        .toArray()
        .map((neighbor: cytoscape.NodeSingular) => String(neighbor.data('label') ?? neighbor.id()));

      onSelect({
        ...(node.data() as Record<string, unknown>),
        relationship_count: node.connectedEdges().length,
        connected_nodes: connectedNodes,
      });
    });
    cy.on('tap', (event) => {
      if (event.target === cy) {
        cy.elements().removeClass('dimmed hovered');
        onSelect({});
      }
    });

    return () => {
      cyRef.current = null;
      cy.destroy();
    };
  }, [elements, onSelect]);

  const zoomIn = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom(Math.min(cy.maxZoom(), cy.zoom() * 1.2));
  };

  const zoomOut = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom(Math.max(cy.minZoom(), cy.zoom() / 1.2));
  };

  const fitGraph = () => {
    cyRef.current?.fit(undefined, 48);
  };

  return (
    <div className="relative h-full min-h-[560px]">
      <div ref={containerRef} className="graph-canvas" aria-label="Interactive evidence relationship graph" />
      <div className="absolute right-3 top-3 flex items-center gap-1 rounded-lg border bg-background/95 p-1 shadow-sm" aria-label="Graph controls">
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" aria-label="Zoom in" title="Zoom in" onClick={zoomIn}>
          <Plus className="h-4 w-4" />
        </Button>
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" aria-label="Zoom out" title="Zoom out" onClick={zoomOut}>
          <Minus className="h-4 w-4" />
        </Button>
        <span className="mx-0.5 h-5 w-px bg-border" />
        <Button type="button" variant="ghost" size="icon" className="h-8 w-8" aria-label="Fit graph to view" title="Fit graph to view" onClick={fitGraph}>
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>
      <p className="pointer-events-none absolute bottom-3 left-3 rounded-md border bg-background/90 px-2 py-1 text-[10px] text-muted-foreground">
        Hover for labels · Select a node to focus its relationships
      </p>
    </div>
  );
}
