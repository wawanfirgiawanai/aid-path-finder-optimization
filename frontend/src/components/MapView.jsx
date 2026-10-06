import React, { useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, Marker, Polyline, CircleMarker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';
import { useApp } from '../contexts/AppContext';

const OSM_TILES = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

const startIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/></svg>`;
const endIconSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="14" height="14"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>`;

function makeIcon(bg, svg, size = 24) {
  return L.divIcon({
    className: '', iconSize: [size, size], iconAnchor: [size / 2, size / 2],
    html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:${bg};border:2px solid white;display:flex;align-items:center;justify-content:center;box-shadow:0 0 8px ${bg}80">${svg}</div>`
  });
}

const startIcon = makeIcon('#3B82F6', startIconSvg);
const endIcon = makeIcon('#22C55E', endIconSvg);
const blockedIcon = L.divIcon({
  className: '', iconSize: [18, 18], iconAnchor: [9, 9],
  html: `<div style="width:18px;height:18px;border-radius:50%;background:#EF4444;border:2px solid white;display:flex;align-items:center;justify-content:center;box-shadow:0 0 6px #EF444480"><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></div>`
});
const centerIcon = L.divIcon({
  className: '', iconSize: [20, 20], iconAnchor: [10, 10],
  html: `<div style="width:20px;height:20px;border-radius:50%;background:#F59E0B;border:2px solid white;display:flex;align-items:center;justify-content:center;box-shadow:0 0 8px #F59E0B80"><svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3"><circle cx="12" cy="12" r="3"/><line x1="12" y1="2" x2="12" y2="6"/><line x1="12" y1="18" x2="12" y2="22"/><line x1="2" y1="12" x2="6" y2="12"/><line x1="18" y1="12" x2="22" y2="12"/></svg></div>`
});

const ALGO_COLORS = { dijkstra:'#3B82F6', astar:'#8B5CF6', bfs:'#F97316', ga:'#22C55E', aco:'#EF4444', ga_es:'#06B6D4', aco_es:'#EC4899', hybrid:'#B45309' };

function ClickHandler({ onMapClick, active }) {
  useMapEvents({ click(e) { if (active) onMapClick(e.latlng); } });
  return null;
}

function TileSwapper({ theme }) {
  const map = useMap();
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current) map.removeLayer(ref.current);
    ref.current = L.tileLayer(OSM_TILES, { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' });
    ref.current.addTo(map);
    // Apply dark filter via CSS on the tile pane
    const tilePane = map.getPane('tilePane');
    if (tilePane) {
      tilePane.style.filter = theme === 'dark' ? 'invert(1) hue-rotate(180deg) brightness(0.8) contrast(1.2)' : 'none';
    }
  }, [theme, map]);
  return null;
}

function FlyToCenter({ center }) {
  const map = useMap();
  const prevCenter = useRef(center);
  useEffect(() => {
    if (center && (center.lat !== prevCenter.current.lat || center.lng !== prevCenter.current.lng)) {
      map.flyTo([center.lat, center.lng], 15, { duration: 1 });
      prevCenter.current = center;
    }
  }, [center, map]);
  return null;
}

function HeatmapLayer({ show, edgesData }) {
  const map = useMap();
  const heatLayerRef = useRef(null);

  const heatPoints = useMemo(() => {
    if (!edgesData?.features) return [];
    const points = [];
    for (const feature of edgesData.features) {
      const coords = feature.geometry?.coordinates;
      const risk = feature.properties?.risk ?? 0.5;
      if (!coords || coords.length < 2) continue;
      // Use edge midpoint for heat data
      const midIdx = Math.floor(coords.length / 2);
      const [lng, lat] = coords[midIdx];
      points.push([lat, lng, risk]);
      // Also add start and end for denser coverage
      if (coords.length > 2) {
        points.push([coords[0][1], coords[0][0], risk * 0.6]);
        points.push([coords[coords.length - 1][1], coords[coords.length - 1][0], risk * 0.6]);
      }
    }
    return points;
  }, [edgesData]);

  useEffect(() => {
    if (!map) return;

    // Remove existing layer
    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
    }

    if (show && heatPoints.length > 0) {
      heatLayerRef.current = L.heatLayer(heatPoints, {
        radius: 20,
        blur: 25,
        maxZoom: 17,
        max: 1.0,
        minOpacity: 0.3,
        gradient: {
          0.0: '#22C55E',
          0.3: '#84CC16',
          0.5: '#EAB308',
          0.7: '#F97316',
          1.0: '#EF4444'
        }
      }).addTo(map);
    }

    return () => {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current);
        heatLayerRef.current = null;
      }
    };
  }, [map, show, heatPoints]);

  return null;
}

export default function MapView() {
  const { theme, graphData, startNodes, endNodes, routeResults, comparisonResults,
          selectMode, isRemovingEdges, handleMapClick, riskThresholds, AGENT_COLORS,
          removedEdgeMarkers, selectedCompAlgo, initCenter, showHeatmap } = useApp();
  const geoKey = useRef(0);
  const edgesData = graphData?.edges;
  useEffect(() => { geoKey.current += 1; }, [edgesData]);

  const riskColor = (risk) => {
    if (risk <= riskThresholds.low_max) return '#22C55E';
    if (risk <= riskThresholds.medium_max) return '#EAB308';
    return '#EF4444';
  };

  const edgeStyle = (feature) => ({
    color: riskColor(feature.properties?.risk ?? 0.5), weight: 2, opacity: showHeatmap ? 0.25 : 0.6
  });

  // Main route results (optimization)
  const agentRoutes = useMemo(() => {
    if (selectedCompAlgo && comparisonResults) return [];
    if (!routeResults?.routes) return [];
    return routeResults.routes.map((r, i) => ({
      positions: r.route_geometry?.map(c => [c[0], c[1]]) || [],
      color: AGENT_COLORS[i % AGENT_COLORS.length], label: r.agent_id
    }));
  }, [routeResults, AGENT_COLORS, selectedCompAlgo, comparisonResults]);

  // Comparison routes
  const compRoutes = useMemo(() => {
    if (!comparisonResults) return [];
    if (selectedCompAlgo) {
      const r = comparisonResults.find(c => c.algorithm === selectedCompAlgo);
      if (!r?.routes) return [];
      return r.routes.map((route) => ({
        positions: route.route_geometry?.map(c => [c[0], c[1]]) || [],
        color: ALGO_COLORS[selectedCompAlgo] || '#fff', label: `${selectedCompAlgo}: ${route.agent_id}`
      }));
    }
    const routes = [];
    comparisonResults.forEach((cr) => {
      cr.routes?.forEach((route) => {
        routes.push({
          positions: route.route_geometry?.map(c => [c[0], c[1]]) || [],
          color: ALGO_COLORS[cr.algorithm] || '#888', label: `${cr.algorithm}: ${route.agent_id}`
        });
      });
    });
    return routes;
  }, [comparisonResults, selectedCompAlgo]);

  const active = !!selectMode || isRemovingEdges;
  const cursor = isRemovingEdges ? 'cursor-crosshair' : selectMode ? 'cursor-crosshair' : '';

  const modeLabel = selectMode === 'start' ? 'Click map to set START point (zoom in for precision)'
    : selectMode === 'end' ? 'Click map to set DESTINATION (zoom in for precision)'
    : selectMode === 'center' ? 'Click map to set CENTER point for initialization'
    : null;

  return (
    <div className={`map-area ${cursor}`} data-testid="map-container">
      <MapContainer center={[initCenter.lat, initCenter.lng]} zoom={15} style={{ width: '100%', height: '100%' }} zoomControl={true}>
        <TileSwapper theme={theme} />
        <FlyToCenter center={initCenter} />
        <ClickHandler onMapClick={handleMapClick} active={active} />
        {edgesData && <GeoJSON key={`e-${geoKey.current}`} data={edgesData} style={edgeStyle} />}

        {/* Heatmap overlay */}
        <HeatmapLayer show={showHeatmap} edgesData={edgesData} />

        {/* Optimization routes */}
        {agentRoutes.map((ar, i) => ar.positions.length > 0 && (
          <Polyline key={`route-${i}`} positions={ar.positions}
            pathOptions={{ color: ar.color, weight: 5, opacity: 0.9 }} />
        ))}

        {/* Comparison routes */}
        {compRoutes.map((cr, i) => cr.positions.length > 0 && (
          <Polyline key={`comp-${i}`} positions={cr.positions}
            pathOptions={{ color: cr.color, weight: 4, opacity: 0.8, dashArray: selectedCompAlgo ? null : '8 4' }} />
        ))}

        {/* Start markers */}
        {startNodes.map((n, i) => (
          <Marker key={`s-${i}`} position={[n.lat, n.lng]} icon={startIcon} />
        ))}

        {/* End markers */}
        {endNodes.map((n, i) => (
          <Marker key={`e-${i}`} position={[n.lat, n.lng]} icon={endIcon} />
        ))}

        {/* Blocked road X markers */}
        {removedEdgeMarkers.map((m, i) => (
          <Marker key={`blocked-${i}`} position={[m.lat, m.lng]} icon={blockedIcon} />
        ))}

        {/* Center marker when selecting */}
        {selectMode === 'center' && (
          <Marker position={[initCenter.lat, initCenter.lng]} icon={centerIcon} />
        )}
      </MapContainer>

      {modeLabel && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] bg-blue-600 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-lg animate-pulse">
          {modeLabel}
        </div>
      )}
      {isRemovingEdges && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] bg-red-600 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-lg animate-pulse">
          Click on a road to block it (X marker will appear)
        </div>
      )}

      {/* Heatmap legend overlay */}
      {showHeatmap && (
        <div className="absolute bottom-4 left-4 z-[1000] bg-card/90 backdrop-blur-sm border border-border rounded-lg p-3 shadow-lg" data-testid="heatmap-legend">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Risk Heatmap</p>
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] text-muted-foreground">Low</span>
            <div className="h-2 flex-1 rounded-full" style={{
              background: 'linear-gradient(to right, #22C55E, #84CC16, #EAB308, #F97316, #EF4444)'
            }} />
            <span className="text-[9px] text-muted-foreground">High</span>
          </div>
        </div>
      )}
    </div>
  );
}
