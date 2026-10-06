import { useState, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function useRisk({ setGraphData, setIsLoading, setRouteResults, setComparisonResults }) {
  const [riskThresholds, setRiskThresholds] = useState({ low_max: 0.33, medium_max: 0.66 });

  const updateRisks = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await axios.post(`${API}/risk/update`, { mode: 'random' });
      if (res.data.edges) setGraphData(prev => ({ ...prev, edges: res.data.edges, nodes: res.data.nodes }));
      setRouteResults(null);
      setComparisonResults(null);
    } finally { setIsLoading(false); }
  }, [setGraphData, setIsLoading, setRouteResults, setComparisonResults]);

  return { riskThresholds, setRiskThresholds, updateRisks };
}
