import { useState, useCallback } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export function useRouting({ startNodes, endNodes, algoParams, forceDistribution }) {
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('dijkstra');
  const [routeResults, setRouteResults] = useState(null);
  const [comparisonResults, setComparisonResults] = useState(null);
  const [benchmarkResults, setBenchmarkResults] = useState(null);
  const [selectedCompAlgo, setSelectedCompAlgo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const optimizeRoute = useCallback(async () => {
    if (startNodes.length === 0 || endNodes.length === 0) return;
    setIsLoading(true);
    try {
      const starts = startNodes.map(n => ({ node_id: n.id, agents: n.agents || 1 }));
      const destinations = endNodes.map(n => ({ node_id: n.id }));
      const res = await axios.post(`${API}/route/optimize`, {
        starts, destinations, algorithm: selectedAlgorithm, algo_params: algoParams,
        force_distribution: forceDistribution
      }, { timeout: 120000 });
      setRouteResults(res.data);
      return res.data;
    } finally { setIsLoading(false); }
  }, [startNodes, endNodes, selectedAlgorithm, algoParams, forceDistribution]);

  const compareAlgorithms = useCallback(async () => {
    if (startNodes.length === 0 || endNodes.length === 0) return;
    setIsLoading(true);
    try {
      const starts = startNodes.map(n => ({ node_id: n.id, agents: n.agents || 1 }));
      const destinations = endNodes.map(n => ({ node_id: n.id }));
      const algos = ['dijkstra', 'astar', 'bfs', 'ga', 'aco', 'ga_es', 'aco_es', 'hybrid'];
      const res = await axios.post(`${API}/route/compare`, {
        starts, destinations, algorithms: algos, algo_params: algoParams,
        force_distribution: forceDistribution
      }, { timeout: 180000 });
      setComparisonResults(res.data.results);
      return res.data.results;
    } finally { setIsLoading(false); }
  }, [startNodes, endNodes, algoParams, forceDistribution]);

  const runBenchmark = useCallback(async (runsPerAlgo) => {
    if (startNodes.length === 0 || endNodes.length === 0) return;
    setIsLoading(true);
    try {
      const starts = startNodes.map(n => ({ node_id: n.id, agents: n.agents || 1 }));
      const destinations = endNodes.map(n => ({ node_id: n.id }));
      const algos = ['dijkstra', 'astar', 'bfs', 'ga', 'ga_es', 'aco', 'aco_es', 'hybrid'];
      const res = await axios.post(`${API}/route/benchmark`, {
        starts, destinations, algorithms: algos,
        runs_per_algo: runsPerAlgo, algo_params: algoParams,
        force_distribution: forceDistribution
      }, { timeout: 300000 });
      setBenchmarkResults(res.data.results);
      return res.data.results;
    } finally { setIsLoading(false); }
  }, [startNodes, endNodes, algoParams, forceDistribution]);

  const clearResults = useCallback(() => {
    setRouteResults(null);
    setComparisonResults(null);
    setSelectedCompAlgo(null);
    setBenchmarkResults(null);
  }, []);

  return {
    selectedAlgorithm, setSelectedAlgorithm,
    routeResults, setRouteResults, comparisonResults, setComparisonResults,
    benchmarkResults, setBenchmarkResults, selectedCompAlgo, setSelectedCompAlgo,
    isLoading, setIsLoading,
    optimizeRoute, compareAlgorithms, runBenchmark, clearResults
  };
}
