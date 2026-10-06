import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Progress } from './ui/progress';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { FlaskConical, Play, Square, Loader2, CheckCircle2, XCircle } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const PHASES = ['tune', 'main', 'scale', 'report'];
const PHASE_LABEL = { tune: 'Tuning', main: 'Main test cases', scale: 'Scalability', report: 'Statistics & figures' };
const ALGO_ORDER = ['Dijkstra', 'A*', 'BFS', 'GA', 'ACO', 'Hybrid A*-GA'];
const PROPOSED = 'Hybrid A*-GA';
const fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? '—'
  : Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }));
const fmtP = (p) => (p < 1e-3 ? Number(p).toExponential(1) : Number(p).toFixed(4));
const byAlgo = (a, b) => ALGO_ORDER.indexOf(a.algorithm) - ALGO_ORDER.indexOf(b.algorithm);

function Th({ children, className = '' }) {
  return <th className={`px-2 py-1 text-left font-semibold text-muted-foreground whitespace-nowrap ${className}`}>{children}</th>;
}
function Td({ children, className = '' }) {
  return <td className={`px-2 py-1 font-mono whitespace-nowrap ${className}`}>{children}</td>;
}

function MainTable({ rows }) {
  const groups = [...new Set(rows.map(r => r.scenario))];
  return (
    <div className="overflow-auto max-h-[52vh] border rounded">
      <table className="w-full text-[11px]">
        <thead className="sticky top-0 bg-background border-b">
          <tr><Th>Scenario</Th><Th>Algorithm</Th><Th>Mean cost (5 cases)</Th><Th>Std over runs</Th>
            <Th>vs. Dijkstra</Th><Th>Gap to optimum</Th><Th>Optimum hits</Th><Th>Time (ms)</Th></tr>
        </thead>
        <tbody>
          {groups.map(g => rows.filter(r => r.scenario === g).sort(byAlgo).map((r, i) => (
            <tr key={`${g}-${r.algorithm}`} className={`${i === 0 ? 'border-t' : ''} ${r.algorithm === PROPOSED ? 'bg-amber-500/10 font-semibold' : ''}`}>
              <Td>{i === 0 ? g : ''}</Td><Td>{r.algorithm}</Td><Td>{fmt(r.cost_mean)}</Td><Td>{fmt(r.cost_std_runs)}</Td>
              <Td>{fmt(r.vs_dijkstra_pct, 2)} %</Td><Td>{r.gap_pct === null ? '—' : `${fmt(r.gap_pct, 2)} %`}</Td>
              <Td>{r.hit_opt === null ? '—' : `${r.hit_opt}/${r.runs}`}</Td><Td>{fmt(r.time_mean_ms)}</Td>
            </tr>)))}
        </tbody>
      </table>
    </div>
  );
}

function CasesTable({ rows }) {
  const [group, setGroup] = useState('all');
  const groups = ['all', ...new Set(rows.map(r => r.group))];
  const shown = rows.filter(r => group === 'all' || r.group === group);
  const ids = [...new Set(shown.map(r => r.case_id))];
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1">
        {groups.map(g => (
          <Button key={g} size="sm" variant={g === group ? 'default' : 'outline'} className="h-6 px-2 text-[10px]"
            onClick={() => setGroup(g)}>{g}</Button>))}
      </div>
      <div className="overflow-auto max-h-[48vh] border rounded">
        <table className="w-full text-[11px]">
          <thead className="sticky top-0 bg-background border-b">
            <tr><Th>Test case</Th><Th>Algorithm</Th><Th>Cost mean ± std</Th><Th>vs. Dijkstra</Th><Th>Optimum</Th>
              <Th>Optimum hits</Th><Th>Time (ms)</Th></tr>
          </thead>
          <tbody>
            {ids.map(id => shown.filter(r => r.case_id === id).sort(byAlgo).map((r, i) => (
              <tr key={`${id}-${r.algorithm}`} className={`${i === 0 ? 'border-t' : ''} ${r.algorithm === PROPOSED ? 'bg-amber-500/10 font-semibold' : ''}`}>
                <Td>{i === 0 ? id : ''}</Td><Td>{r.algorithm}</Td><Td>{fmt(r.cost_mean)} ± {fmt(r.cost_std)}</Td>
                <Td>{fmt(r.vs_dijkstra_pct, 2)} %</Td><Td>{r.optimum === null ? '—' : fmt(r.optimum)}</Td>
                <Td>{r.hit_opt === null ? '—' : `${r.hit_opt}/${r.runs}`}</Td><Td>{fmt(r.time_mean_ms)}</Td>
              </tr>)))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScaleTable({ stats, scale }) {
  const groups = [...new Set(scale.map(r => r.group))];
  return (
    <div className="space-y-3">
      <div className="border rounded overflow-auto">
        <table className="w-full text-[11px]">
          <thead className="border-b"><tr><Th>Subset</Th><Th>Hybrid vs.</Th><Th>Better / tie / worse</Th><Th>Mean cost change</Th>
            <Th>Largest saving</Th><Th>p (Wilcoxon–Holm)</Th></tr></thead>
          <tbody>{stats.map(r => (
            <tr key={`${r.subset}-${r.vs}`} className="border-t"><Td>{r.subset}</Td><Td>{r.vs}</Td>
              <Td>{r.hybrid_better} / {r.ties} / {r.hybrid_worse}</Td><Td>{fmt(r.mean_change_pct, 2)} %</Td>
              <Td>{fmt(r.largest_saving_pct, 1)} %</Td><Td>{fmtP(r.p_holm)}</Td></tr>))}
          </tbody>
        </table>
      </div>
      <div className="border rounded overflow-auto">
        <table className="w-full text-[11px]">
          <thead className="border-b"><tr><Th>Destinations</Th>{ALGO_ORDER.map(a => <Th key={a}>{a}: cost vs. Dijkstra · time</Th>)}</tr></thead>
          <tbody>{groups.map(g => {
            const rs = scale.filter(r => r.group === g);
            return (
              <tr key={g} className="border-t"><Td>{rs[0]?.n_dest}</Td>
                {ALGO_ORDER.map(a => { const r = rs.find(x => x.algorithm === a);
                  return <Td key={a}>{r ? `${fmt(r.vs_dijkstra_pct, 1)} % · ${fmt(r.time_mean_ms, 0)} ms` : '—'}</Td>; })}
              </tr>);
          })}</tbody>
        </table>
      </div>
    </div>
  );
}

export default function ExperimentsPanel({ open, onOpenChange }) {
  const [status, setStatus] = useState(null);
  const [results, setResults] = useState(null);
  const [jobs, setJobs] = useState('');
  const [starting, setStarting] = useState(false);
  const lastState = useRef(null);
  const logRef = useRef(null);

  const loadResults = useCallback(async (runId) => {
    try {
      const res = await axios.get(`${API}/experiments/results`, { params: runId ? { run_id: runId } : {} });
      setResults(res.data);
    } catch { setResults(null); }
  }, []);

  const poll = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/experiments/status`);
      const st = res.data;
      setStatus(st);
      if (lastState.current === 'running' && st.state !== 'running') {
        if (st.state === 'done') { toast.success('Paper experiments finished'); loadResults(st.run_id); }
        else if (st.state === 'failed') toast.error('Experiment run failed — see the log');
      }
      lastState.current = st.state;
    } catch { /* backend not reachable: keep last status */ }
  }, [loadResults]);

  useEffect(() => {
    if (!open) return undefined;
    poll();
    loadResults();
    const id = setInterval(poll, 1500);
    return () => clearInterval(id);
  }, [open, poll, loadResults]);

  useEffect(() => { if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [status?.log?.length]);

  const start = async () => {
    setStarting(true);
    try {
      const n = parseInt(jobs, 10);
      await axios.post(`${API}/experiments/run`, { jobs: Number.isFinite(n) && n > 0 ? n : null });
      lastState.current = 'running';
      setResults(null);
      await poll();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not start the experiments');
    } finally { setStarting(false); }
  };

  const cancel = async () => {
    await axios.post(`${API}/experiments/cancel`);
    poll();
  };

  const running = status?.state === 'running';
  const pct = Math.round((status?.overall || 0) * 100);
  const mins = (s) => `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`;
  const rep = results?.reproduction;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-[95vw] max-h-[92vh] overflow-y-auto overflow-x-hidden" data-testid="experiments-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><FlaskConical className="w-4 h-4" />Paper experiments</DialogTitle>
          <DialogDescription className="text-xs">
            One click runs the whole study of the paper on one road network (Mamuju, 1,500 m) and its 40 documented
            test cases: tuning of GA, ACO and the hybrid A*-GA, 20 main cases (SA-SD, SA-MD, MA-SD, MA-MD; 30 runs
            each), 20 scalability cases (5–30 destinations; 10 runs each), the statistical tests and the figures.
            Results go to experiments/runs/&lt;run id&gt; and never overwrite the published results.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-end gap-2">
          <Button onClick={start} disabled={running || starting} className="h-9 gap-1.5" data-testid="run-experiments-btn">
            {running || starting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            {running ? 'Running…' : 'Run all paper experiments'}
          </Button>
          {running && (
            <Button variant="outline" onClick={cancel} className="h-9 gap-1.5" data-testid="cancel-experiments-btn">
              <Square className="w-3.5 h-3.5" />Cancel
            </Button>
          )}
          <div className="ml-auto flex items-center gap-2">
            <label className="text-[11px] text-muted-foreground">Worker processes</label>
            <Input value={jobs} onChange={e => setJobs(e.target.value)} placeholder="auto" disabled={running}
              className="h-8 w-20 text-xs font-mono" data-testid="experiments-jobs" />
          </div>
        </div>

        {status && status.state !== 'idle' && (
          <div className="space-y-2 border rounded p-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold flex items-center gap-1.5">
                {status.state === 'done' && <CheckCircle2 className="w-4 h-4 text-green-600" />}
                {(status.state === 'failed' || status.state === 'cancelled') && <XCircle className="w-4 h-4 text-red-600" />}
                {running ? `Phase ${status.phase_index}/${status.phase_total}: ${status.phase_name || 'starting'}`
                  : `Run ${status.run_id}: ${status.state}`}
              </span>
              <span className="font-mono text-muted-foreground">{pct}% · {mins(status.elapsed_s)}</span>
            </div>
            <Progress value={pct} />
            <div className="flex gap-1 flex-wrap">
              {PHASES.map((p, i) => {
                const doneP = status.state === 'done' || i + 1 < status.phase_index;
                const cur = running && i + 1 === status.phase_index;
                return (
                  <Badge key={p} variant={doneP ? 'default' : 'outline'} className={`text-[10px] ${cur ? 'border-primary' : ''}`}>
                    {PHASE_LABEL[p]}{cur && status.progress_total ? ` ${status.progress_done}/${status.progress_total}` : ''}
                  </Badge>);
              })}
            </div>
            <pre ref={logRef} className="text-[10px] leading-tight bg-muted/40 rounded p-2 max-h-32 overflow-auto font-mono whitespace-pre-wrap break-all">
              {(status.log || []).join('\n')}
            </pre>
          </div>
        )}

        {results ? (
          <div className="space-y-2 min-w-0">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-semibold">Results of run {results.run_id}</span>
              {rep && (
                <Badge variant={rep.mismatches === 0 ? 'default' : 'destructive'} className="text-[10px]">
                  {rep.mismatches === 0
                    ? `Reproduces the paper: ${rep.compared_runs} runs, identical cost and distance`
                    : `${rep.mismatches} of ${rep.compared_runs} runs differ from the paper`}
                </Badge>
              )}
              {results.excel && (
                <a href={`${API}/experiments/excel/${results.run_id}`} download
                   className="inline-flex items-center rounded-md bg-emerald-700 hover:bg-emerald-800 text-white px-2.5 py-1 text-[11px] font-medium">
                  Download Excel (all results + figures)
                </a>
              )}
              {results.summary?.friedman_all_cases && (
                <Badge variant="outline" className="text-[10px]">
                  Friedman over {results.summary.friedman_all_cases.cases} cases: χ² = {fmt(results.summary.friedman_all_cases.statistic, 1)}, p = {fmtP(results.summary.friedman_all_cases.p)}
                </Badge>
              )}
            </div>
            <Tabs defaultValue="main">
              <TabsList className="h-8">
                <TabsTrigger value="main" className="text-xs">Main scenarios</TabsTrigger>
                <TabsTrigger value="cases" className="text-xs">Test cases</TabsTrigger>
                <TabsTrigger value="scale" className="text-xs">Statistics &amp; scalability</TabsTrigger>
                <TabsTrigger value="params" className="text-xs">Tuned parameters</TabsTrigger>
                <TabsTrigger value="figures" className="text-xs">Figures</TabsTrigger>
              </TabsList>
              <TabsContent value="main"><MainTable rows={results.main} /></TabsContent>
              <TabsContent value="cases"><CasesTable rows={results.cases} /></TabsContent>
              <TabsContent value="scale"><ScaleTable stats={results.stats} scale={results.scale} /></TabsContent>
              <TabsContent value="params">
                <p className="text-[11px] text-muted-foreground mb-2">
                  Evaluation uses the frozen parameters of the paper (dataset/tuned_params.json). The tuning phase is
                  re-run for transparency; it breaks ties within 0.5 % by run time, which differs between machines.
                </p>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {Object.entries(results.frozen_params || results.tuned_params).map(([algo, p]) => (
                    <div key={algo} className="border rounded p-2">
                      <p className="text-xs font-semibold mb-1 uppercase">{algo}</p>
                      <div className="flex justify-between text-[10px] text-muted-foreground mb-0.5">
                        <span>parameter</span><span>used (paper) · re-tuned</span>
                      </div>
                      {Object.entries(p).map(([k, v]) => {
                        const re = results.tuned_params?.[algo]?.[k];
                        return (
                          <div key={k} className="flex justify-between text-[11px] font-mono">
                            <span className="text-muted-foreground">{k.replace(/^(ga|aco|hga)_/, '')}</span>
                            <span>{v} · <span className={re !== v ? 'text-amber-600' : 'text-muted-foreground'}>{re ?? '—'}</span></span>
                          </div>);
                      })}
                    </div>))}
                </div>
              </TabsContent>
              <TabsContent value="figures">
                <div className="grid md:grid-cols-2 gap-3">
                  {[...(results.journal_figures || []), ...results.figures].map(f => (
                    <figure key={f} className="border rounded p-2 bg-white">
                      <img src={`${API}/experiments/figure/${results.run_id}/${f}`} alt={f} className="w-full" />
                      <figcaption className="text-[10px] text-gray-600 mt-1 font-mono">{f}</figcaption>
                    </figure>))}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        ) : (!running && <p className="text-xs text-muted-foreground">No completed run yet. Press the button to start.</p>)}
      </DialogContent>
    </Dialog>
  );
}
