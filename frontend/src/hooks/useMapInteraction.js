import { useState, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function useMapInteraction({ findNearestNode, setStartNodes, setEndNodes, setGraphData }) {
  const [selectMode, setSelectMode] = useState(null);
  const [isRemovingEdges, setIsRemovingEdges] = useState(false);
  const [removedEdgesCount, setRemovedEdgesCount] = useState(0);
  const [removedEdgeMarkers, setRemovedEdgeMarkers] = useState([]);
  const [initCenter, setInitCenter] = useState({ lat: -2.692, lng: 118.898 }); // Mamuju (paper study area)
  const [showHeatmap, setShowHeatmap] = useState(false);

  const removeEdge = useCallback(async (lat, lng) => {
    try {
      const res = await axios.post(`${API}/graph/remove-edge`, { lat, lng });
      if (res.data.edges) setGraphData(prev => ({ ...prev, edges: res.data.edges }));
      setRemovedEdgesCount(res.data.removed_count || 0);
      if (res.data.removed_midpoint) {
        setRemovedEdgeMarkers(prev => [...prev, res.data.removed_midpoint]);
      }
      return res.data;
    } catch { return null; }
  }, [setGraphData]);

  const restoreEdges = useCallback(async () => {
    const res = await axios.post(`${API}/graph/restore-edges`);
    if (res.data.edges) setGraphData(prev => ({ ...prev, edges: res.data.edges }));
    setRemovedEdgesCount(0);
    setRemovedEdgeMarkers([]);
    return res.data;
  }, [setGraphData]);

  const handleMapClick = useCallback(async (latlng) => {
    if (selectMode === 'center') {
      setInitCenter({ lat: latlng.lat, lng: latlng.lng });
      setSelectMode(null);
      return;
    }
    if (isRemovingEdges) {
      await removeEdge(latlng.lat, latlng.lng);
      return;
    }
    if (!selectMode) return;
    try {
      const node = await findNearestNode(latlng.lat, latlng.lng);
      if (selectMode === 'start') {
        setStartNodes(prev => [...prev, { ...node, agents: 1, label: `S${prev.length + 1}` }]);
      } else if (selectMode === 'end') {
        setEndNodes(prev => [...prev, { ...node, label: `E${prev.length + 1}` }]);
      }
      setSelectMode(null);
    } catch (_err) { /* nearest node lookup failed */ }
  }, [selectMode, isRemovingEdges, findNearestNode, removeEdge, setStartNodes, setEndNodes]);

  const resetInteraction = useCallback(() => {
    setRemovedEdgesCount(0);
    setRemovedEdgeMarkers([]);
  }, []);

  return {
    selectMode, setSelectMode, isRemovingEdges, setIsRemovingEdges,
    removedEdgesCount, removedEdgeMarkers, initCenter, setInitCenter,
    showHeatmap, setShowHeatmap,
    removeEdge, restoreEdges, handleMapClick, resetInteraction
  };
}
