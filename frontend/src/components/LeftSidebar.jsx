import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../contexts/AppContext';
import { t } from '../lib/translations';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { Slider } from './ui/slider';
import { Switch } from './ui/switch';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';
import { toast } from 'sonner';
import {
  MapPin, Play, BarChart3, RefreshCw, Crosshair, X, Loader2, Network, Trash2,
  Plus, Upload, RotateCcw, Scissors, ShieldCheck, Users, Flame
} from 'lucide-react';

export default function LeftSidebar() {
  const {
    language, graphSummary, isGraphLoading, isLoading,
    startNodes, setStartNodes, endNodes, setEndNodes,
    selectedAlgorithm, setSelectedAlgorithm, algoParams, setAlgoParams,
    riskThresholds, setRiskThresholds,
    selectMode, setSelectMode, isRemovingEdges, setIsRemovingEdges, removedEdgesCount,
    routeResults, comparisonResults,
    initGraph, resetGraph, optimizeRoute, compareAlgorithms, updateRisks,
    restoreEdges, importJSON, clearResults, initCenter, setInitCenter,
    forceDistribution, setForceDistribution,
    showHeatmap, setShowHeatmap
  } = useApp();

  const [lat, setLat] = useState(initCenter.lat.toString());
  const [lng, setLng] = useState(initCenter.lng.toString());
  const [radius, setRadius] = useState('1500');
  const fileRef = useRef(null);

  // Sync lat/lng when initCenter changes (from map click)
  useEffect(() => {
    setLat(initCenter.lat.toFixed(6));
    setLng(initCenter.lng.toFixed(6));
  }, [initCenter]);

  const handleInit = async () => {
    try {
      const r = await initGraph(parseFloat(lat), parseFloat(lng), parseInt(radius));
      toast.success(`Graph: ${r.nodes_count} nodes, ${r.edges_count} edges (${r.source})`);
    } catch { toast.error('Failed to initialize'); }
  };

  const handleOptimize = async () => {
    if (!startNodes.length || !endNodes.length) { toast.error(t(language, 'selectPoints')); return; }
    try {
      const r = await optimizeRoute();
      if (r?.summary) toast.success(`Route found: ${r.summary.total_cost.toFixed(1)} cost, ${r.summary.agents_used} agents`);
    } catch { toast.error('Optimization failed'); }
  };

  const handleCompare = async () => {
    if (!startNodes.length || !endNodes.length) { toast.error(t(language, 'selectPoints')); return; }
    try { await compareAlgorithms(); toast.success('Comparison complete'); } catch { toast.error('Comparison failed'); }
  };

  const handleReset = async () => { await resetGraph(); toast.success('Graph cleared'); };

  const updateStartAgents = (idx, agents) => {
    setStartNodes(prev => prev.map((n, i) => i === idx ? { ...n, agents: Math.max(1, parseInt(agents) || 1) } : n));
  };

  const removeStart = (idx) => setStartNodes(prev => prev.filter((_, i) => i !== idx));
  const removeEnd = (idx) => setEndNodes(prev => prev.filter((_, i) => i !== idx));

  const handleFileImport = (e) => {
    const file = e.target.files?.[0];
    if (file) { importJSON(file); toast.success('Session imported'); }
  };

  const updateParam = (key, val) => setAlgoParams(prev => ({ ...prev, [key]: val }));

  const showGaParams = ['ga', 'ga_es'].includes(selectedAlgorithm);
  const showAcoParams = ['aco', 'aco_es'].includes(selectedAlgorithm);

  return (
    <div className="left-sidebar" data-testid="left-sidebar">
      <Accordion type="multiple" defaultValue={['network', 'points', 'algorithm', 'actions']} className="space-y-0">
        {/* Network Setup */}
        <AccordionItem value="network" className="border-b-0">
          <AccordionTrigger className="py-2 text-xs font-semibold uppercase tracking-widest hover:no-underline">
            {t(language, 'initGraph')}
          </AccordionTrigger>
          <AccordionContent className="pb-3 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-[10px] text-muted-foreground">{t(language, 'latitude')}</label>
                <Input data-testid="input-lat" value={lat} onChange={e => setLat(e.target.value)} className="h-7 text-xs font-mono" /></div>
              <div><label className="text-[10px] text-muted-foreground">{t(language, 'longitude')}</label>
                <Input data-testid="input-lng" value={lng} onChange={e => setLng(e.target.value)} className="h-7 text-xs font-mono" /></div>
            </div>
            <div><label className="text-[10px] text-muted-foreground">{t(language, 'radius')}</label>
              <Input data-testid="input-radius" value={radius} onChange={e => setRadius(e.target.value)} className="h-7 text-xs font-mono" /></div>
            <div className="flex gap-2">
              <Button data-testid="init-graph-btn" className="flex-1 h-8 text-xs" onClick={handleInit} disabled={isGraphLoading}>
                {isGraphLoading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <Network className="w-3 h-3 mr-1" />}
                {isGraphLoading ? 'Loading...' : 'Initialize'}
              </Button>
              <Button data-testid="set-center-btn" variant={selectMode === 'center' ? 'default' : 'outline'} className="h-8 w-8 p-0"
                onClick={() => setSelectMode(selectMode === 'center' ? null : 'center')} title="Click map to set center">
                <Crosshair className="w-3.5 h-3.5" />
              </Button>
              <Button data-testid="reset-btn" variant="destructive" className="h-8 w-8 p-0" onClick={handleReset} disabled={!graphSummary}>
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
            {graphSummary && (
              <div className="flex gap-1.5 flex-wrap">
                <Badge variant="secondary" className="text-[10px] font-mono">{graphSummary.nodes_count} nodes</Badge>
                <Badge variant="secondary" className="text-[10px] font-mono">{graphSummary.edges_count} edges</Badge>
                <Badge variant="outline" className="text-[10px] font-mono">{graphSummary.source}</Badge>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        <Separator />

        {/* Points */}
        <AccordionItem value="points" className="border-b-0">
          <AccordionTrigger className="py-2 text-xs font-semibold uppercase tracking-widest hover:no-underline">
            Start & Destinations
          </AccordionTrigger>
          <AccordionContent className="pb-3 space-y-3">
            {/* Start Points */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-blue-500">Start Points</span>
                <div className="flex gap-1">
                  {startNodes.length > 0 && (
                    <Button variant="ghost" size="sm" className="h-5 text-[9px] px-1 text-destructive" onClick={() => setStartNodes([])}>
                      Clear All
                    </Button>
                  )}
                  <Button data-testid="add-start-btn" variant={selectMode === 'start' ? 'default' : 'outline'} size="sm"
                    className="h-6 text-[10px] px-2" onClick={() => setSelectMode(selectMode === 'start' ? null : 'start')} disabled={!graphSummary}>
                    <Plus className="w-2.5 h-2.5 mr-0.5" />Add
                  </Button>
                </div>
              </div>
              {startNodes.map((n, i) => (
                <div key={n.id} className="flex items-center gap-1.5 bg-blue-500/10 border border-blue-500/20 rounded px-2 py-1 mb-1">
                  <div className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />
                  <span className="text-[10px] font-mono text-blue-400 flex-1">{n.label} ({n.lat.toFixed(4)}, {n.lng.toFixed(4)})</span>
                  <div className="flex items-center gap-0.5">
                    <Users className="w-2.5 h-2.5 text-muted-foreground" />
                    <Input value={n.agents} onChange={e => updateStartAgents(i, e.target.value)} className="h-5 w-8 text-[10px] font-mono p-0 text-center" />
                  </div>
                  <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={() => removeStart(i)}><X className="w-2.5 h-2.5" /></Button>
                </div>
              ))}
            </div>
            {/* Destination Points */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-green-500">Evacuation Points</span>
                <div className="flex gap-1">
                  {endNodes.length > 0 && (
                    <Button variant="ghost" size="sm" className="h-5 text-[9px] px-1 text-destructive" onClick={() => setEndNodes([])}>
                      Clear All
                    </Button>
                  )}
                  <Button data-testid="add-end-btn" variant={selectMode === 'end' ? 'default' : 'outline'} size="sm"
                    className="h-6 text-[10px] px-2" onClick={() => setSelectMode(selectMode === 'end' ? null : 'end')} disabled={!graphSummary}>
                    <Plus className="w-2.5 h-2.5 mr-0.5" />Add
                  </Button>
                </div>
              </div>
              {endNodes.map((n, i) => (
                <div key={n.id} className="flex items-center gap-1.5 bg-green-500/10 border border-green-500/20 rounded px-2 py-1 mb-1">
                  <div className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
                  <span className="text-[10px] font-mono text-green-400 flex-1">{n.label} ({n.lat.toFixed(4)}, {n.lng.toFixed(4)})</span>
                  <Button variant="ghost" size="sm" className="h-5 w-5 p-0" onClick={() => removeEnd(i)}><X className="w-2.5 h-2.5" /></Button>
                </div>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>

        <Separator />

        {/* Algorithm */}
        <AccordionItem value="algorithm" className="border-b-0">
          <AccordionTrigger className="py-2 text-xs font-semibold uppercase tracking-widest hover:no-underline">
            {t(language, 'algorithm')}
          </AccordionTrigger>
          <AccordionContent className="pb-3 space-y-3">
            <Select value={selectedAlgorithm} onValueChange={setSelectedAlgorithm}>
              <SelectTrigger className="h-8 text-xs" data-testid="algorithm-select-trigger"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="dijkstra">Dijkstra</SelectItem>
                <SelectItem value="astar">A* (A-Star)</SelectItem>
                <SelectItem value="bfs">BFS</SelectItem>
                <SelectItem value="ga">Genetic Algorithm</SelectItem>
                <SelectItem value="ga_es">GA + Early Stopping</SelectItem>
                <SelectItem value="aco">Ant Colony (ACO)</SelectItem>
                <SelectItem value="aco_es">ACO + Early Stopping</SelectItem>
                <SelectItem value="hybrid">Hybrid A*-GA (proposed)</SelectItem>
              </SelectContent>
            </Select>
            {showGaParams && (
              <div className="space-y-2 p-2 border rounded bg-muted/30">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">GA Parameters</span>
                <ParamRow label="Population" value={algoParams.ga_population} onChange={v => updateParam('ga_population', parseInt(v))} />
                <ParamRow label="Generations" value={algoParams.ga_generations} onChange={v => updateParam('ga_generations', parseInt(v))} />
                <ParamRow label="Crossover Rate" value={algoParams.ga_crossover_rate} onChange={v => updateParam('ga_crossover_rate', parseFloat(v))} step="0.05" />
                <ParamRow label="Mutation Rate" value={algoParams.ga_mutation_rate} onChange={v => updateParam('ga_mutation_rate', parseFloat(v))} step="0.01" />
                <ParamRow label="Tournament K" value={algoParams.ga_tournament_k} onChange={v => updateParam('ga_tournament_k', parseInt(v))} />
                <ParamRow label="Elitism" value={algoParams.ga_elitism} onChange={v => updateParam('ga_elitism', parseInt(v))} />
                {selectedAlgorithm === 'ga_es' && (
                  <ParamRow label="Stagnation Limit" value={algoParams.ga_stagnation_limit} onChange={v => updateParam('ga_stagnation_limit', parseInt(v))} />
                )}
              </div>
            )}
            {selectedAlgorithm === 'hybrid' && (
              <div className="space-y-2 p-2 border rounded bg-muted/30">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Hybrid A*-GA - Allocation GA (Level 2)</span>
                <ParamRow label="Population" value={algoParams.hga_population} onChange={v => updateParam('hga_population', parseInt(v))} />
                <ParamRow label="Generations" value={algoParams.hga_generations} onChange={v => updateParam('hga_generations', parseInt(v))} />
                <ParamRow label="Crossover Rate" value={algoParams.hga_crossover_rate} onChange={v => updateParam('hga_crossover_rate', parseFloat(v))} step="0.05" />
                <ParamRow label="Inversion Rate" value={algoParams.hga_mutation_rate} onChange={v => updateParam('hga_mutation_rate', parseFloat(v))} step="0.05" />
                <ParamRow label="Tournament K" value={algoParams.hga_tournament_k} onChange={v => updateParam('hga_tournament_k', parseInt(v))} />
                <ParamRow label="Elitism" value={algoParams.hga_elitism} onChange={v => updateParam('hga_elitism', parseInt(v))} />
                <ParamRow label="Stagnation Limit" value={algoParams.hga_stagnation_limit} onChange={v => updateParam('hga_stagnation_limit', parseInt(v))} />
              </div>
            )}
            {showAcoParams && (
              <div className="space-y-2 p-2 border rounded bg-muted/30">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">ACO Parameters</span>
                <ParamRow label="Ants" value={algoParams.aco_ants} onChange={v => updateParam('aco_ants', parseInt(v))} />
                <ParamRow label="Iterations" value={algoParams.aco_iterations} onChange={v => updateParam('aco_iterations', parseInt(v))} />
                <ParamRow label="Alpha" value={algoParams.aco_alpha} onChange={v => updateParam('aco_alpha', parseFloat(v))} step="0.1" />
                <ParamRow label="Beta" value={algoParams.aco_beta} onChange={v => updateParam('aco_beta', parseFloat(v))} step="0.1" />
                <ParamRow label="Evaporation" value={algoParams.aco_evaporation} onChange={v => updateParam('aco_evaporation', parseFloat(v))} step="0.05" />
                {selectedAlgorithm === 'aco_es' && (
                  <ParamRow label="Stagnation Limit" value={algoParams.aco_stagnation_limit} onChange={v => updateParam('aco_stagnation_limit', parseInt(v))} />
                )}
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        <Separator />

        {/* Risk & Simulation */}
        <AccordionItem value="risk" className="border-b-0">
          <AccordionTrigger className="py-2 text-xs font-semibold uppercase tracking-widest hover:no-underline">
            Risk & Simulation
          </AccordionTrigger>
          <AccordionContent className="pb-3 space-y-3">
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground">Low Risk Max: {riskThresholds.low_max.toFixed(2)}</span>
              <Slider value={[riskThresholds.low_max * 100]} max={100} step={1}
                onValueChange={([v]) => setRiskThresholds(p => ({ ...p, low_max: v / 100, medium_max: Math.max(p.medium_max, v / 100 + 0.01) }))}
                className="mt-1" data-testid="risk-low-slider" />
            </div>
            <div>
              <span className="text-[10px] font-semibold text-muted-foreground">Medium Risk Max: {riskThresholds.medium_max.toFixed(2)}</span>
              <Slider value={[riskThresholds.medium_max * 100]} max={100} step={1}
                onValueChange={([v]) => setRiskThresholds(p => ({ ...p, medium_max: Math.max(v / 100, p.low_max + 0.01) }))}
                className="mt-1" data-testid="risk-medium-slider" />
            </div>
            <div className="flex gap-1 text-[10px]">
              <span className="flex items-center gap-1"><span className="w-3 h-1 rounded bg-[#22C55E]" />Low 0-{riskThresholds.low_max.toFixed(2)}</span>
              <span className="flex items-center gap-1"><span className="w-3 h-1 rounded bg-[#EAB308]" />Med {riskThresholds.low_max.toFixed(2)}-{riskThresholds.medium_max.toFixed(2)}</span>
              <span className="flex items-center gap-1"><span className="w-3 h-1 rounded bg-[#EF4444]" />High {riskThresholds.medium_max.toFixed(2)}-1.0</span>
            </div>
            <div className="flex items-center justify-between p-2 border rounded bg-muted/30">
              <div className="flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-orange-500" />
                <div>
                  <p className="text-[10px] font-semibold">Risk Heatmap</p>
                  <p className="text-[9px] text-muted-foreground">Overlay visualisasi risiko</p>
                </div>
              </div>
              <Switch checked={showHeatmap} onCheckedChange={setShowHeatmap} disabled={!graphSummary} data-testid="heatmap-toggle" />
            </div>
            <Button variant="ghost" className="w-full h-7 text-[10px]" onClick={updateRisks} disabled={isLoading || !graphSummary}>
              <RefreshCw className="w-3 h-3 mr-1" />{t(language, 'regenerateRisk')}
            </Button>
            <Separator />
            <div className="flex gap-1.5">
              <Button variant={isRemovingEdges ? 'destructive' : 'outline'} className="flex-1 h-7 text-[10px]"
                onClick={() => setIsRemovingEdges(!isRemovingEdges)} disabled={!graphSummary} data-testid="remove-edge-btn">
                <Scissors className="w-3 h-3 mr-1" />{isRemovingEdges ? 'Stop Removing' : 'Remove Roads'}
              </Button>
              {removedEdgesCount > 0 && (
                <Button variant="outline" className="h-7 text-[10px] px-2" onClick={() => { restoreEdges(); toast.success('Roads restored'); }}>
                  <RotateCcw className="w-3 h-3 mr-1" />Restore ({removedEdgesCount})
                </Button>
              )}
            </div>
          </AccordionContent>
        </AccordionItem>

        <Separator />

        {/* Actions */}
        <AccordionItem value="actions" className="border-b-0">
          <AccordionTrigger className="py-2 text-xs font-semibold uppercase tracking-widest hover:no-underline">
            Actions
          </AccordionTrigger>
          <AccordionContent className="pb-3 space-y-2">
            <div className="flex items-center justify-between p-2 border rounded bg-muted/30">
              <div>
                <p className="text-[10px] font-semibold">Force Agent Distribution</p>
                <p className="text-[9px] text-muted-foreground">Pastikan semua agent mendapat tujuan</p>
              </div>
              <Switch checked={forceDistribution} onCheckedChange={setForceDistribution} data-testid="force-distribution-toggle" />
            </div>
            <Button data-testid="optimize-btn" className="w-full h-9 text-xs font-semibold" onClick={handleOptimize}
              disabled={isLoading || !startNodes.length || !endNodes.length}>
              {isLoading ? <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1" />}
              {t(language, 'findRoute')}
            </Button>
            <Button data-testid="compare-btn" variant="outline" className="w-full h-8 text-xs" onClick={handleCompare}
              disabled={isLoading || !startNodes.length || !endNodes.length}>
              <BarChart3 className="w-3 h-3 mr-1" />{t(language, 'compareAll')}
            </Button>
            <Button data-testid="clear-results-btn" variant="ghost" className="w-full h-7 text-[10px] text-destructive" onClick={clearResults}
              disabled={!routeResults && !comparisonResults}>
              <Trash2 className="w-3 h-3 mr-1" />Clear Route Results
            </Button>
            <div className="flex gap-1.5">
              <Button variant="ghost" className="flex-1 h-7 text-[10px]" onClick={() => fileRef.current?.click()}>
                <Upload className="w-3 h-3 mr-1" />Import
              </Button>
              <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={handleFileImport} />
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}

function ParamRow({ label, value, onChange, step = "1" }) {
  return (
    <div className="flex items-center justify-between">
      <label className="text-[10px] text-muted-foreground">{label}</label>
      <Input value={value} onChange={e => onChange(e.target.value)} step={step}
        className="h-6 w-16 text-[10px] font-mono text-right p-1" type="number" />
    </div>
  );
}
