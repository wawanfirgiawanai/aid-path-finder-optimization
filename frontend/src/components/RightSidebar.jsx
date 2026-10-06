import React, { useState, useMemo } from 'react';
import { useApp } from '../contexts/AppContext';
import { t } from '../lib/translations';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Route, Timer, Navigation, ShieldAlert, Info, Download, Image, Users, Loader2, FlaskConical } from 'lucide-react';
import html2canvas from 'html2canvas';

const ALGO_COLORS = { dijkstra:'#3B82F6', astar:'#8B5CF6', bfs:'#F97316', ga:'#22C55E', aco:'#EF4444', ga_es:'#06B6D4', aco_es:'#EC4899', hybrid:'#B45309' };
const ALGO_NAMES = { dijkstra:'Dijkstra', astar:'A*', bfs:'BFS', ga:'GA', aco:'ACO', ga_es:'GA-ES', aco_es:'ACO-ES', hybrid:'Hybrid A*-GA' };

export default function RightSidebar() {
  const { language, routeResults, comparisonResults, graphSummary, theme, exportJSON, exportCSV, AGENT_COLORS, riskThresholds,
          selectedCompAlgo, setSelectedCompAlgo, clearResults, benchmarkResults, runBenchmark, isLoading, startNodes, endNodes } = useApp();
  const tc = theme === 'dark' ? '#fafafa' : '#18181b';
  const riskColor = (r) => r <= riskThresholds.low_max ? '#22C55E' : r <= riskThresholds.medium_max ? '#EAB308' : '#EF4444';
  const [benchRuns, setBenchRuns] = useState(5);
  const tickStyle = useMemo(() => ({ fontSize: 8, fill: tc }), [tc]);
  const tooltipStyle = useMemo(() => ({
    background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '4px', fontSize: '10px'
  }), []);

  const exportImage = async () => {
    try {
      const el = document.querySelector('.map-area');
      if (!el) return;
      // Hide UI overlays temporarily
      const overlays = el.querySelectorAll('.absolute');
      overlays.forEach(o => o.style.display = 'none');
      // Hide leaflet controls for cleaner export
      const controls = el.querySelectorAll('.leaflet-control-container');
      controls.forEach(c => c.style.display = 'none');
      const canvas = await html2canvas(el, {
        useCORS: true, allowTaint: true, scale: 2,
        backgroundColor: null,
        logging: false,
        ignoreElements: (element) => {
          return element.id === 'emergent-badge' || element.classList?.contains('leaflet-control-attribution');
        }
      });
      // Restore
      overlays.forEach(o => o.style.display = '');
      controls.forEach(c => c.style.display = '');
      canvas.toBlob(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'optiroute_map.png'; a.click();
        URL.revokeObjectURL(url);
      }, 'image/png');
    } catch (_e) { /* export failed silently */ }
  };

  return (
    <div className="right-sidebar" data-testid="right-sidebar">
      <Tabs defaultValue="results" className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-3 h-8">
          <TabsTrigger value="results" className="text-[10px]" data-testid="tab-results">{t(language, 'results')}</TabsTrigger>
          <TabsTrigger value="comparison" className="text-[10px]" data-testid="tab-comparison">{t(language, 'comparison')}</TabsTrigger>
          <TabsTrigger value="benchmark" className="text-[10px]" data-testid="tab-benchmark">Benchmark</TabsTrigger>
        </TabsList>

        {/* RESULTS */}
        <TabsContent value="results" className="flex-1 mt-3 space-y-3 overflow-y-auto">
          {routeResults?.routes?.length > 0 ? (
            <>
              {/* Summary */}
              <div className="grid grid-cols-2 gap-2">
                <MC label={t(language,'totalDistance')} value={routeResults.summary.total_distance.toFixed(1)} unit="m" icon={<Navigation className="w-3 h-3"/>} tid="total-distance"/>
                <MC label={t(language,'totalCost')} value={routeResults.summary.total_cost.toFixed(1)} icon={<Route className="w-3 h-3"/>} tid="total-cost"/>
                <MC label={t(language,'computationTime')} value={routeResults.summary.computation_time_ms.toFixed(1)} unit="ms" icon={<Timer className="w-3 h-3"/>} tid="computation-time"/>
                <MC label="Avg Risk" value={routeResults.summary.avg_risk.toFixed(3)} icon={<ShieldAlert className="w-3 h-3"/>} tid="avg-risk" vc={riskColor(routeResults.summary.avg_risk)}/>
              </div>
              <div className="flex gap-2 text-[10px]">
                <Badge variant="secondary" className="font-mono"><Users className="w-2.5 h-2.5 mr-1"/>{routeResults.summary.agents_used} agents</Badge>
                <Badge variant="secondary" className="font-mono">{routeResults.summary.destinations_covered}/{routeResults.summary.total_destinations} covered</Badge>
                <Badge variant="outline" className="font-mono">{ALGO_NAMES[routeResults.algorithm]}</Badge>
              </div>

              {/* Per-agent routes */}
              <div className="space-y-2">
                {routeResults.routes.map((r, i) => (
                  <div key={r.agent_id} className="metric-card" data-testid={`agent-route-${i}`}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-3 h-3 rounded-full shrink-0" style={{background: AGENT_COLORS[i % AGENT_COLORS.length]}}/>
                      <span className="text-xs font-semibold">{r.agent_id}</span>
                      <span className="text-[10px] font-mono text-muted-foreground">{r.route_label}</span>
                    </div>
                    {/* Segment table */}
                    <div className="border rounded overflow-hidden">
                      <Table>
                        <TableHeader><TableRow className="hover:bg-transparent">
                          <TableHead className="text-[9px] h-5 px-1.5">Route</TableHead>
                          <TableHead className="text-[9px] h-5 px-1.5 text-right">Dist</TableHead>
                          <TableHead className="text-[9px] h-5 px-1.5 text-right">Risk</TableHead>
                          <TableHead className="text-[9px] h-5 px-1.5 text-right">Cost</TableHead>
                        </TableRow></TableHeader>
                        <TableBody>
                          {r.segments?.map((s, j) => (
                            <TableRow key={j}>
                              <TableCell className="text-[10px] font-mono px-1.5 py-0.5">{s.route_label}</TableCell>
                              <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5">{s.distance.toFixed(1)}</TableCell>
                              <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5" style={{color:riskColor(s.avg_risk)}}>{s.avg_risk.toFixed(3)}</TableCell>
                              <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5">{s.cost.toFixed(1)}</TableCell>
                            </TableRow>
                          ))}
                          <TableRow className="font-semibold bg-muted/30">
                            <TableCell className="text-[10px] font-mono px-1.5 py-0.5">Total</TableCell>
                            <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5">{r.total_distance.toFixed(1)}</TableCell>
                            <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5" style={{color:riskColor(r.avg_risk)}}>{r.avg_risk.toFixed(3)}</TableCell>
                            <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5">{r.total_cost.toFixed(1)}</TableCell>
                          </TableRow>
                        </TableBody>
                      </Table>
                    </div>
                  </div>
                ))}
              </div>

              {/* Export */}
              <div className="flex gap-1.5">
                <Button variant="outline" size="sm" className="flex-1 h-7 text-[10px]" onClick={exportJSON} data-testid="export-json-btn">
                  <Download className="w-3 h-3 mr-1"/>JSON
                </Button>
                <Button variant="outline" size="sm" className="flex-1 h-7 text-[10px]" onClick={exportCSV} data-testid="export-csv-btn">
                  <Download className="w-3 h-3 mr-1"/>CSV
                </Button>
                <Button variant="outline" size="sm" className="flex-1 h-7 text-[10px]" onClick={exportImage} data-testid="export-img-btn">
                  <Image className="w-3 h-3 mr-1"/>PNG
                </Button>
              </div>
            </>
          ) : (<Empty language={language} graphSummary={graphSummary}/>)}
        </TabsContent>

        {/* COMPARISON */}
        <TabsContent value="comparison" className="flex-1 mt-3 space-y-3 overflow-y-auto">
          {comparisonResults?.length > 0 ? (
            <>
              {/* Route selector - click to show on map */}
              <div>
                <p className="section-label">Show Route on Map (click to select)</p>
                <div className="flex flex-wrap gap-1">
                  <Button variant={!selectedCompAlgo ? 'default' : 'outline'} size="sm" className="h-6 text-[9px] px-2"
                    onClick={() => setSelectedCompAlgo(null)} data-testid="comp-show-all">All</Button>
                  {comparisonResults.map(r => (
                    <Button key={r.algorithm} variant={selectedCompAlgo === r.algorithm ? 'default' : 'outline'} size="sm"
                      className="h-6 text-[9px] px-2 font-mono" style={selectedCompAlgo === r.algorithm ? {backgroundColor: ALGO_COLORS[r.algorithm], color: '#fff'} : {}}
                      onClick={() => setSelectedCompAlgo(selectedCompAlgo === r.algorithm ? null : r.algorithm)}
                      data-testid={`comp-select-${r.algorithm}`}>
                      {ALGO_NAMES[r.algorithm]}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Summary Table */}
              <div className="border rounded-md overflow-hidden" data-testid="comparison-table">
                <Table>
                  <TableHeader><TableRow className="hover:bg-transparent">
                    <TableHead className="text-[9px] h-6 px-1.5">Algorithm</TableHead>
                    <TableHead className="text-[9px] h-6 px-1.5 text-right">Agents</TableHead>
                    <TableHead className="text-[9px] h-6 px-1.5 text-right">Dist (m)</TableHead>
                    <TableHead className="text-[9px] h-6 px-1.5 text-right">Risk</TableHead>
                    <TableHead className="text-[9px] h-6 px-1.5 text-right">Cost</TableHead>
                    <TableHead className="text-[9px] h-6 px-1.5 text-right">Time</TableHead>
                  </TableRow></TableHeader>
                  <TableBody>
                    {comparisonResults.map(r => (
                      <TableRow key={r.algorithm} data-testid={`comp-row-${r.algorithm}`}
                        className={`cursor-pointer transition-colors ${selectedCompAlgo === r.algorithm ? 'bg-accent' : 'hover:bg-muted/50'}`}
                        onClick={() => setSelectedCompAlgo(selectedCompAlgo === r.algorithm ? null : r.algorithm)}>
                        <TableCell className="px-1.5 py-1">
                          <Badge className="text-[9px] font-mono px-1.5 py-0" style={{backgroundColor:ALGO_COLORS[r.algorithm],color:'#fff'}}>{ALGO_NAMES[r.algorithm]}</Badge>
                        </TableCell>
                        <TableCell className="text-[10px] font-mono text-right px-1.5 py-1">{r.summary.agents_used}</TableCell>
                        <TableCell className="text-[10px] font-mono text-right px-1.5 py-1">{r.summary.total_distance.toFixed(1)}</TableCell>
                        <TableCell className="text-[10px] font-mono text-right px-1.5 py-1" style={{color:riskColor(r.summary.avg_risk)}}>{r.summary.avg_risk.toFixed(3)}</TableCell>
                        <TableCell className="text-[10px] font-mono text-right px-1.5 py-1 font-semibold">{r.summary.total_cost.toFixed(1)}</TableCell>
                        <TableCell className="text-[10px] font-mono text-right px-1.5 py-1">{r.summary.computation_time_ms.toFixed(1)}ms</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <Separator />

              {/* Charts */}
              <div>
                <p className="section-label">{t(language,'totalCost')}</p>
                <div className="h-36">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonResults.map(r=>({name:ALGO_NAMES[r.algorithm],cost:r.summary.total_cost,algo:r.algorithm}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))"/>
                      <XAxis dataKey="name" tick={tickStyle}/><YAxis tick={tickStyle}/>
                      <Tooltip contentStyle={tooltipStyle}/>
                      <Bar dataKey="cost" radius={[3,3,0,0]}>{comparisonResults.map((e,i)=>(<Cell key={e.algorithm} fill={ALGO_COLORS[e.algorithm]||'#888'}/>))}</Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div>
                <p className="section-label">{t(language,'computationTime')}</p>
                <div className="h-36">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={comparisonResults.map(r=>({name:ALGO_NAMES[r.algorithm],time:r.summary.computation_time_ms,algo:r.algorithm}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))"/>
                      <XAxis dataKey="name" tick={tickStyle}/><YAxis tick={tickStyle}/>
                      <Tooltip contentStyle={tooltipStyle}/>
                      <Bar dataKey="time" radius={[3,3,0,0]}>{comparisonResults.map((e,i)=>(<Cell key={e.algorithm} fill={ALGO_COLORS[e.algorithm]||'#888'}/>))}</Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Export */}
              <div className="flex gap-1.5">
                <Button variant="outline" size="sm" className="flex-1 h-7 text-[10px]" onClick={exportJSON}><Download className="w-3 h-3 mr-1"/>JSON</Button>
                <Button variant="outline" size="sm" className="flex-1 h-7 text-[10px]" onClick={exportCSV}><Download className="w-3 h-3 mr-1"/>CSV</Button>
                <Button variant="outline" size="sm" className="flex-1 h-7 text-[10px]" onClick={exportImage}><Image className="w-3 h-3 mr-1"/>PNG</Button>
              </div>
            </>
          ) : (<Empty language={language} graphSummary={graphSummary}/>)}
        </TabsContent>

        {/* BENCHMARK TAB */}
        <TabsContent value="benchmark" className="flex-1 mt-3 space-y-3 overflow-y-auto">
          {/* Controls */}
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <label className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">Runs per algorithm</label>
              <Input type="number" min={1} max={50} value={benchRuns} onChange={e => setBenchRuns(Math.max(1, parseInt(e.target.value) || 1))}
                className="h-8 text-xs font-mono mt-1" data-testid="benchmark-runs-input" />
            </div>
            <Button className="h-8 text-xs mt-4" onClick={async () => { try { await runBenchmark(benchRuns); } catch {} }}
              disabled={isLoading || !startNodes.length || !endNodes.length} data-testid="run-benchmark-btn">
              {isLoading ? <Loader2 className="w-3 h-3 mr-1 animate-spin" /> : <FlaskConical className="w-3 h-3 mr-1" />}
              Run Benchmark
            </Button>
          </div>

          {benchmarkResults?.length > 0 ? (
            <>
              {/* Summary stats table */}
              <div>
                <p className="section-label">Summary Statistics ({benchmarkResults[0]?.total_runs} runs each)</p>
                <div className="border rounded-md overflow-hidden" data-testid="benchmark-summary-table">
                  <Table>
                    <TableHeader><TableRow className="hover:bg-transparent">
                      <TableHead className="text-[8px] h-6 px-1">Algo</TableHead>
                      <TableHead className="text-[8px] h-6 px-1 text-right">Cost Avg</TableHead>
                      <TableHead className="text-[8px] h-6 px-1 text-right">Cost Min</TableHead>
                      <TableHead className="text-[8px] h-6 px-1 text-right">Cost Max</TableHead>
                      <TableHead className="text-[8px] h-6 px-1 text-right">StdDev</TableHead>
                      <TableHead className="text-[8px] h-6 px-1 text-right">Time Avg</TableHead>
                    </TableRow></TableHeader>
                    <TableBody>
                      {benchmarkResults.map(b => (
                        <TableRow key={b.algorithm} data-testid={`bench-summary-${b.algorithm}`}>
                          <TableCell className="px-1 py-1">
                            <Badge className="text-[8px] font-mono px-1 py-0" style={{backgroundColor:ALGO_COLORS[b.algorithm],color:'#fff'}}>
                              {ALGO_NAMES[b.algorithm]}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-[10px] font-mono text-right px-1 py-1 font-semibold">{b.stats.cost_avg.toFixed(1)}</TableCell>
                          <TableCell className="text-[10px] font-mono text-right px-1 py-1">{b.stats.cost_min.toFixed(1)}</TableCell>
                          <TableCell className="text-[10px] font-mono text-right px-1 py-1">{b.stats.cost_max.toFixed(1)}</TableCell>
                          <TableCell className="text-[10px] font-mono text-right px-1 py-1 text-muted-foreground">{b.stats.cost_stdev.toFixed(2)}</TableCell>
                          <TableCell className="text-[10px] font-mono text-right px-1 py-1">{b.stats.time_avg.toFixed(1)}ms</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>

              <Separator />

              {/* Per-algorithm detail runs */}
              {benchmarkResults.map(b => (
                <div key={b.algorithm}>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge className="text-[9px] font-mono px-1.5 py-0" style={{backgroundColor:ALGO_COLORS[b.algorithm],color:'#fff'}}>
                      {ALGO_NAMES[b.algorithm]}
                    </Badge>
                    <span className="text-[10px] text-muted-foreground">{b.total_runs} runs</span>
                  </div>
                  <div className="border rounded-md overflow-hidden mb-2" data-testid={`bench-detail-${b.algorithm}`}>
                    <Table>
                      <TableHeader><TableRow className="hover:bg-transparent">
                        <TableHead className="text-[8px] h-5 px-1.5">Run</TableHead>
                        <TableHead className="text-[8px] h-5 px-1.5 text-right">Distance</TableHead>
                        <TableHead className="text-[8px] h-5 px-1.5 text-right">Risk</TableHead>
                        <TableHead className="text-[8px] h-5 px-1.5 text-right">Cost</TableHead>
                        <TableHead className="text-[8px] h-5 px-1.5 text-right">Time (ms)</TableHead>
                      </TableRow></TableHeader>
                      <TableBody>
                        {b.runs.map(run => (
                          <TableRow key={run.run}>
                            <TableCell className="text-[10px] font-mono px-1.5 py-0.5">#{run.run}</TableCell>
                            <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5">{run.total_distance.toFixed(1)}</TableCell>
                            <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5" style={{color:riskColor(run.avg_risk)}}>{run.avg_risk.toFixed(3)}</TableCell>
                            <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5">{run.total_cost.toFixed(1)}</TableCell>
                            <TableCell className="text-[10px] font-mono text-right px-1.5 py-0.5">{run.computation_time_ms.toFixed(1)}</TableCell>
                          </TableRow>
                        ))}
                        {/* Stats row */}
                        <TableRow className="bg-muted/30 font-semibold">
                          <TableCell className="text-[9px] font-mono px-1.5 py-0.5">AVG</TableCell>
                          <TableCell className="text-[9px] font-mono text-right px-1.5 py-0.5">{b.stats.dist_avg.toFixed(1)}</TableCell>
                          <TableCell className="text-[9px] font-mono text-right px-1.5 py-0.5" style={{color:riskColor(b.stats.risk_avg)}}>{b.stats.risk_avg.toFixed(3)}</TableCell>
                          <TableCell className="text-[9px] font-mono text-right px-1.5 py-0.5">{b.stats.cost_avg.toFixed(1)}</TableCell>
                          <TableCell className="text-[9px] font-mono text-right px-1.5 py-0.5">{b.stats.time_avg.toFixed(1)}</TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ))}

              {/* Avg Cost Chart */}
              <div>
                <p className="section-label">Average Cost Comparison</p>
                <div className="h-36">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={benchmarkResults.map(b=>({name:ALGO_NAMES[b.algorithm],cost:b.stats.cost_avg,algo:b.algorithm}))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))"/>
                      <XAxis dataKey="name" tick={tickStyle}/><YAxis tick={tickStyle}/>
                      <Tooltip contentStyle={tooltipStyle}/>
                      <Bar dataKey="cost" radius={[3,3,0,0]}>{benchmarkResults.map((e,i)=>(<Cell key={e.algorithm} fill={ALGO_COLORS[e.algorithm]||'#888'}/>))}</Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-32 text-center">
              <FlaskConical className="w-8 h-8 text-muted-foreground mb-2" />
              <p className="text-xs text-muted-foreground">Set start/end points, then run benchmark</p>
              <p className="text-[10px] text-muted-foreground mt-1">Each algorithm runs N times to measure stability</p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function MC({label,value,unit,icon,tid,vc}){
  return(<div className="metric-card" data-testid={tid}><div className="flex items-center gap-1 text-muted-foreground mb-0.5">{icon}<span className="metric-label mt-0">{label}</span></div><div className="flex items-baseline gap-1"><span className="metric-value text-xl" style={vc?{color:vc}:undefined}>{value}</span>{unit&&<span className="text-[10px] text-muted-foreground font-mono">{unit}</span>}</div></div>);
}

function Empty({language,graphSummary}){
  return(<div className="flex flex-col items-center justify-center h-40 text-center"><Info className="w-8 h-8 text-muted-foreground mb-2"/><p className="text-xs text-muted-foreground">{graphSummary?t(language,'selectPoints'):t(language,'noData')}</p></div>);
}
