import { useCallback } from 'react';

export function useExport({ startNodes, endNodes, routeResults, comparisonResults, algoParams, riskThresholds }) {
  const exportJSON = useCallback(() => {
    const data = { startNodes, endNodes, routeResults, comparisonResults, algoParams, riskThresholds };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'optiroute_session.json'; a.click();
  }, [startNodes, endNodes, routeResults, comparisonResults, algoParams, riskThresholds]);

  const exportCSV = useCallback(() => {
    if (!comparisonResults && !routeResults) return;
    let rows = [['Algorithm', 'Agent', 'Route', 'Distance (m)', 'Avg Risk', 'Cost', 'Time (ms)']];
    const data = comparisonResults || [routeResults];
    for (const r of data) {
      const algo = r.algorithm || '';
      for (const route of (r.routes || [])) {
        rows.push([algo, route.agent_id, route.route_label, route.total_distance, route.avg_risk, route.total_cost,
                    r.summary?.computation_time_ms || '']);
      }
    }
    const csv = rows.map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'optiroute_results.csv'; a.click();
  }, [routeResults, comparisonResults]);

  const importJSON = useCallback(async (file, setters) => {
    const text = await file.text();
    try {
      const data = JSON.parse(text);
      if (data.startNodes) setters.setStartNodes(data.startNodes);
      if (data.endNodes) setters.setEndNodes(data.endNodes);
      if (data.algoParams) setters.setAlgoParams(data.algoParams);
      if (data.riskThresholds) setters.setRiskThresholds(data.riskThresholds);
      if (typeof data.forceDistribution === 'boolean' && setters.setForceDistribution) {
        setters.setForceDistribution(data.forceDistribution);
      }
    } catch { /* invalid JSON */ }
  }, []);

  return { exportJSON, exportCSV, importJSON };
}
