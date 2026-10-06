import { useState, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function useGraph() {
  const [graphData, setGraphData] = useState(null);
  const [nodesList, setNodesList] = useState([]);
  const [isGraphLoading, setIsGraphLoading] = useState(false);
  const [graphSummary, setGraphSummary] = useState(null);

  const initGraph = useCallback(async (lat, lng, radius) => {
    setIsGraphLoading(true);
    try {
      const res = await axios.post(`${API}/graph/init`, { lat, lng, radius }, { timeout: 120000 });
      setGraphSummary(res.data);
      const gr = await axios.get(`${API}/graph/data`);
      setGraphData(gr.data);
      setNodesList(gr.data.nodes_list || []);
      return res.data;
    } finally {
      setIsGraphLoading(false);
    }
  }, []);

  const resetGraph = useCallback(async () => {
    await axios.post(`${API}/graph/reset`);
    setGraphData(null);
    setNodesList([]);
    setGraphSummary(null);
  }, []);

  const findNearestNode = useCallback(async (lat, lng) => {
    const res = await axios.get(`${API}/graph/nearest`, { params: { lat, lng } });
    return res.data;
  }, []);

  return {
    graphData, setGraphData, nodesList, isGraphLoading, graphSummary, setGraphSummary,
    initGraph, resetGraph, findNearestNode
  };
}
