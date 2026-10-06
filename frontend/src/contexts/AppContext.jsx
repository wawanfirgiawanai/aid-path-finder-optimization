import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useGraph } from '../hooks/useGraph';
import { useRouting } from '../hooks/useRouting';
import { useRisk } from '../hooks/useRisk';
import { useMapInteraction } from '../hooks/useMapInteraction';
import { useExport } from '../hooks/useExport';

const AppContext = createContext();
export function useApp() { return useContext(AppContext); }

const AGENT_COLORS = ['#3B82F6','#8B5CF6','#F97316','#06B6D4','#EC4899','#14B8A6','#F59E0B','#6366F1','#10B981','#EF4444'];

export function AppProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');
  const [language, setLanguage] = useState(() => localStorage.getItem('lang') || 'en');
  const [startNodes, setStartNodes] = useState([]);
  const [endNodes, setEndNodes] = useState([]);
  const [algoParams, setAlgoParams] = useState({
    ga_population: 50, ga_generations: 100, ga_crossover_rate: 0.8,
    ga_mutation_rate: 0.05, ga_tournament_k: 3, ga_elitism: 2,
    ga_stagnation_limit: 10,
    aco_ants: 20, aco_iterations: 50, aco_alpha: 1.0, aco_beta: 2.0,
    aco_evaporation: 0.5, aco_stagnation_limit: 10,
    hga_population: 60, hga_generations: 200, hga_crossover_rate: 0.9,
    hga_mutation_rate: 0.3, hga_tournament_k: 3, hga_elitism: 2,
    hga_stagnation_limit: 50
  });
  const [forceDistribution, setForceDistribution] = useState(false);

  useEffect(() => { document.documentElement.classList.toggle('dark', theme === 'dark'); localStorage.setItem('theme', theme); }, [theme]);
  useEffect(() => { localStorage.setItem('lang', language); }, [language]);

  const toggleTheme = useCallback(() => setTheme(p => p === 'dark' ? 'light' : 'dark'), []);
  const toggleLanguage = useCallback(() => setLanguage(p => p === 'en' ? 'id' : 'en'), []);

  // Graph hook
  const graph = useGraph();

  // Routing hook
  const routing = useRouting({ startNodes, endNodes, algoParams, forceDistribution });

  // Risk hook
  const risk = useRisk({
    setGraphData: graph.setGraphData,
    setIsLoading: routing.setIsLoading,
    setRouteResults: routing.setRouteResults,
    setComparisonResults: routing.setComparisonResults
  });

  // Map interaction hook
  const mapInteraction = useMapInteraction({
    findNearestNode: graph.findNearestNode,
    setStartNodes, setEndNodes,
    setGraphData: graph.setGraphData
  });

  // Export hook
  const exportHook = useExport({
    startNodes, endNodes,
    routeResults: routing.routeResults,
    comparisonResults: routing.comparisonResults,
    algoParams, riskThresholds: risk.riskThresholds
  });

  // Wrap initGraph to also reset points
  const initGraph = useCallback(async (lat, lng, radius) => {
    const result = await graph.initGraph(lat, lng, radius);
    setStartNodes([]); setEndNodes([]);
    routing.setRouteResults(null); routing.setComparisonResults(null);
    mapInteraction.resetInteraction();
    return result;
  }, [graph, routing, mapInteraction]);

  // Wrap resetGraph to also reset points
  const resetGraph = useCallback(async () => {
    await graph.resetGraph();
    setStartNodes([]); setEndNodes([]);
    routing.setRouteResults(null); routing.setComparisonResults(null);
    mapInteraction.resetInteraction();
  }, [graph, routing, mapInteraction]);

  // importJSON wrapper
  const importJSON = useCallback(async (file) => {
    await exportHook.importJSON(file, { setStartNodes, setEndNodes, setAlgoParams, setRiskThresholds: risk.setRiskThresholds,
                                        setForceDistribution });
  }, [exportHook, risk.setRiskThresholds]);

  const value = useMemo(() => ({
    theme, toggleTheme, language, toggleLanguage,
    graphData: graph.graphData, nodesList: graph.nodesList,
    startNodes, setStartNodes, endNodes, setEndNodes,
    selectedAlgorithm: routing.selectedAlgorithm, setSelectedAlgorithm: routing.setSelectedAlgorithm,
    algoParams, setAlgoParams,
    riskThresholds: risk.riskThresholds, setRiskThresholds: risk.setRiskThresholds,
    routeResults: routing.routeResults, setRouteResults: routing.setRouteResults,
    comparisonResults: routing.comparisonResults, setComparisonResults: routing.setComparisonResults,
    isLoading: routing.isLoading, isGraphLoading: graph.isGraphLoading, graphSummary: graph.graphSummary,
    selectMode: mapInteraction.selectMode, setSelectMode: mapInteraction.setSelectMode,
    isRemovingEdges: mapInteraction.isRemovingEdges, setIsRemovingEdges: mapInteraction.setIsRemovingEdges,
    removedEdgesCount: mapInteraction.removedEdgesCount,
    removedEdgeMarkers: mapInteraction.removedEdgeMarkers,
    selectedCompAlgo: routing.selectedCompAlgo, setSelectedCompAlgo: routing.setSelectedCompAlgo,
    initCenter: mapInteraction.initCenter, setInitCenter: mapInteraction.setInitCenter,
    benchmarkResults: routing.benchmarkResults, setBenchmarkResults: routing.setBenchmarkResults,
    forceDistribution, setForceDistribution,
    showHeatmap: mapInteraction.showHeatmap, setShowHeatmap: mapInteraction.setShowHeatmap,
    initGraph, resetGraph,
    optimizeRoute: routing.optimizeRoute, compareAlgorithms: routing.compareAlgorithms,
    updateRisks: risk.updateRisks,
    removeEdge: mapInteraction.removeEdge, restoreEdges: mapInteraction.restoreEdges,
    clearResults: routing.clearResults, runBenchmark: routing.runBenchmark,
    handleMapClick: mapInteraction.handleMapClick,
    exportJSON: exportHook.exportJSON, exportCSV: exportHook.exportCSV, importJSON, AGENT_COLORS
  }), [theme, toggleTheme, language, toggleLanguage, graph.graphData, graph.nodesList,
    startNodes, endNodes, routing.selectedAlgorithm, routing.setSelectedAlgorithm,
    algoParams, risk.riskThresholds, risk.setRiskThresholds,
    routing.routeResults, routing.setRouteResults,
    routing.comparisonResults, routing.setComparisonResults,
    routing.isLoading, graph.isGraphLoading, graph.graphSummary,
    mapInteraction.selectMode, mapInteraction.setSelectMode,
    mapInteraction.isRemovingEdges, mapInteraction.setIsRemovingEdges,
    mapInteraction.removedEdgesCount, mapInteraction.removedEdgeMarkers,
    routing.selectedCompAlgo, routing.setSelectedCompAlgo,
    mapInteraction.initCenter, mapInteraction.setInitCenter,
    routing.benchmarkResults, routing.setBenchmarkResults,
    forceDistribution, mapInteraction.showHeatmap, mapInteraction.setShowHeatmap,
    initGraph, resetGraph, routing.optimizeRoute, routing.compareAlgorithms, risk.updateRisks,
    mapInteraction.removeEdge, mapInteraction.restoreEdges, routing.clearResults,
    routing.runBenchmark, mapInteraction.handleMapClick,
    exportHook.exportJSON, exportHook.exportCSV, importJSON]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
