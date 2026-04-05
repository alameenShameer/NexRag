import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Code2, Database, RefreshCcw, ShieldCheck } from 'lucide-react';
import { KnowledgeGraphEditor } from './KnowledgeGraphEditor';

type KnowledgeTab = 'overview' | 'departments' | 'faculty' | 'facilities' | 'placements' | 'faqs' | 'events' | 'graph' | 'ops';

interface KnowledgeData {
  updated_at?: string | null;
  index_version?: string;
  overview: {
    college?: string;
    location?: string;
    summary?: string;
  };
  departments: Array<any>;
  faculty: Array<any>;
  facilities: Array<any>;
  placements: Array<any>;
  faqs: Array<any>;
  events: Array<any>;
  documents: Array<any>;
}

interface GraphData {
  nodes: Array<any>;
  edges: Array<any>;
}

const EMPTY_DATA: KnowledgeData = {
  overview: {},
  departments: [],
  faculty: [],
  facilities: [],
  placements: [],
  faqs: [],
  events: [],
  documents: [],
};

const EMPTY_GRAPH: GraphData = {
  nodes: [],
  edges: [],
};

async function fetchJson(url: string) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed for ${url}`);
  }
  return response.json();
}

async function fetchKnowledgeBasePanelData({
  includeGraph = false,
  includeOps = false,
}: {
  includeGraph?: boolean;
  includeOps?: boolean;
}) {
  const [knowledgeBase, graph, ingestionStatus, evaluationSummary, evaluationStatus, evaluationMetrics] = await Promise.all([
    fetchJson('http://127.0.0.1:8000/api/knowledge-base'),
    includeGraph ? fetchJson('http://127.0.0.1:8000/api/knowledge-base/graph') : Promise.resolve(null),
    includeOps ? fetchJson('http://127.0.0.1:8000/api/ingestion/status') : Promise.resolve(null),
    includeOps ? fetchJson('http://127.0.0.1:8000/api/evaluation/summary') : Promise.resolve(null),
    includeOps ? fetchJson('http://127.0.0.1:8000/api/evaluation/status') : Promise.resolve(null),
    includeOps ? fetchJson('http://127.0.0.1:8000/api/evaluation/metrics') : Promise.resolve(null),
  ]);

  return {
    knowledgeBase,
    graph,
    ingestionStatus,
    evaluationSummary,
    evaluationStatus,
    evaluationMetrics,
  };
}

export function KnowledgeBasePanel({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<KnowledgeData>(EMPTY_DATA);
  const [graph, setGraph] = useState<GraphData>(EMPTY_GRAPH);
  const [ingestionStatus, setIngestionStatus] = useState<any>(null);
  const [evaluationSummary, setEvaluationSummary] = useState<any>(null);
  const [evaluationStatus, setEvaluationStatus] = useState<any>(null);
  const [evaluationMetrics, setEvaluationMetrics] = useState<any>(null);
  const [developerMode, setDeveloperMode] = useState(false);
  const [activeTab, setActiveTab] = useState<KnowledgeTab>('overview');
  const [showEditor, setShowEditor] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [graphQuery, setGraphQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const shouldLoadGraph = developerMode && activeTab === 'graph';
  const shouldLoadOps = developerMode && activeTab === 'ops';

  const applyRefreshPayload = (payload: {
    knowledgeBase: KnowledgeData;
    graph: GraphData | null;
    ingestionStatus: any;
    evaluationSummary: any;
    evaluationStatus: any;
    evaluationMetrics: any;
  }) => {
    setData(payload.knowledgeBase);
    if (payload.graph) {
      setGraph(payload.graph);
    }
    if (payload.ingestionStatus) {
      setIngestionStatus(payload.ingestionStatus);
    }
    if (payload.evaluationSummary) {
      setEvaluationSummary(payload.evaluationSummary);
    }
    if (payload.evaluationStatus) {
      setEvaluationStatus(payload.evaluationStatus);
    }
    if (payload.evaluationMetrics) {
      setEvaluationMetrics(payload.evaluationMetrics);
    }
  };

  const refresh = async ({
    includeGraph = shouldLoadGraph,
    includeOps = shouldLoadOps,
  }: {
    includeGraph?: boolean;
    includeOps?: boolean;
  } = {}) => {
    const payload = await fetchKnowledgeBasePanelData({ includeGraph, includeOps });
    applyRefreshPayload(payload);
  };

  useEffect(() => {
    let active = true;
    const loadPanel = async () => {
      try {
        const payload = await fetchKnowledgeBasePanelData({
          includeGraph: shouldLoadGraph,
          includeOps: shouldLoadOps,
        });
        if (!active) {
          return;
        }
        applyRefreshPayload(payload);
      } catch (error) {
        if (active) {
          console.error('Knowledge base refresh failed', error);
        }
      }
    };

    loadPanel();
    const interval = window.setInterval(() => {
      loadPanel();
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [shouldLoadGraph, shouldLoadOps]);

  const runRefresh = async () => {
    setIsRefreshing(true);
    try {
      await fetch('http://127.0.0.1:8000/api/ingestion/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true }),
      });
      await refresh({ includeGraph: shouldLoadGraph, includeOps: true });
    } finally {
      setIsRefreshing(false);
    }
  };

  const runEvaluation = async () => {
    await fetch('http://127.0.0.1:8000/api/evaluation/run', { method: 'POST' });
    await refresh({ includeGraph: shouldLoadGraph, includeOps: true });
  };

  const filteredNodes = useMemo(() => {
    const normalized = graphQuery.trim().toLowerCase();
    if (!normalized) {
      return graph.nodes;
    }
    return graph.nodes.filter((node) => `${node.label} ${node.type}`.toLowerCase().includes(normalized));
  }, [graph.nodes, graphQuery]);

  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) || filteredNodes[0] || null;
  const selectedEdges = graph.edges.filter((edge) => edge.source === selectedNode?.id || edge.target === selectedNode?.id);

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'departments' as const, label: 'Departments' },
    { id: 'faculty' as const, label: 'Faculty' },
    { id: 'facilities' as const, label: 'Facilities' },
    { id: 'placements' as const, label: 'Placements' },
    { id: 'faqs' as const, label: 'FAQs' },
    { id: 'events' as const, label: 'Events' },
    ...(developerMode ? [{ id: 'graph' as const, label: 'Graph' }, { id: 'ops' as const, label: 'Developer' }] : []),
  ];

  return (
    <div className="absolute inset-0 z-50 flex flex-col bg-background pt-16">
      <div className="flex items-center justify-between border-b border-border bg-card px-6 py-4">
        <div className="flex items-center gap-3">
          <Database className="h-5 w-5 text-primary" />
          <div>
            <h2 className="text-xl font-semibold text-foreground">Knowledge Base</h2>
            <p className="text-xs text-muted-foreground">Structured MESITAM knowledge view with grounded source content.</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() =>
              setDeveloperMode((value) => {
                const nextValue = !value;
                if (!nextValue && (activeTab === 'graph' || activeTab === 'ops')) {
                  setActiveTab('overview');
                }
                return nextValue;
              })
            }
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
              developerMode ? 'bg-amber-500/15 text-amber-300' : 'bg-muted text-muted-foreground hover:text-foreground'
            }`}
          >
            <Code2 className="h-4 w-4" />
            Developer Mode
          </button>
          <button
            type="button"
            onClick={runRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-2 text-xs font-medium text-primary transition-colors hover:bg-primary/20 disabled:opacity-60"
          >
            <RefreshCcw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh Sources
          </button>
          <button
            type="button"
            onClick={onClose}
            className="flex items-center gap-2 rounded-lg bg-muted px-4 py-2 text-foreground transition-colors hover:bg-muted/80"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Chat
          </button>
        </div>
      </div>

      {showEditor ? <KnowledgeGraphEditor onClose={() => setShowEditor(false)} /> : null}

      <div className="border-b border-border bg-card/60 px-6">
        <div className="flex gap-2 overflow-x-auto py-3">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                activeTab === tab.id ? 'bg-white text-black' : 'bg-muted/40 text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <section className="grid gap-4 md:grid-cols-3">
              <MetricCard label="Indexed Official Docs" value={String(data.documents.length)} />
              <MetricCard label="Departments" value={String(data.departments.length)} />
              <MetricCard label="Faculty Records" value={String(data.faculty.length)} />
            </section>
            <section className="rounded-2xl border border-border bg-card p-5">
              <div className="mb-2 flex items-center gap-2 text-foreground">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <h3 className="text-sm font-semibold">{data.overview.college || 'MESITAM'}</h3>
              </div>
              <p className="text-sm text-muted-foreground">{data.overview.location}</p>
              <p className="mt-4 text-sm leading-7 text-foreground">{data.overview.summary}</p>
              <p className="mt-4 text-xs text-muted-foreground">Index version: {data.index_version || 'unavailable'} • Last update: {data.updated_at || 'pending'}</p>
            </section>
            <TwoColumnSection
              leftTitle="Top FAQs"
              leftItems={data.faqs.slice(0, 5).map((item) => `${item.question}`)}
              rightTitle="Recent Events"
              rightItems={data.events.slice(0, 5).map((item) => `${item.title}${item.posted_on ? ` • ${item.posted_on}` : ''}`)}
            />
          </div>
        )}

        {activeTab === 'departments' && <CardGrid items={data.departments} titleKey="name" subtitleKey="summary" metaKey="courses" />}
        {activeTab === 'faculty' && <CardGrid items={data.faculty} titleKey="name" subtitleKey="designation" metaKey="department" />}
        {activeTab === 'facilities' && <CardGrid items={data.facilities} titleKey="name" subtitleKey="description" />}
        {activeTab === 'placements' && <CardGrid items={data.placements} titleKey="title" subtitleKey="summary" metaKey="highlights" />}
        {activeTab === 'faqs' && <FaqList items={data.faqs} />}
        {activeTab === 'events' && <CardGrid items={data.events} titleKey="title" subtitleKey="summary" metaKey="posted_on" />}

        {activeTab === 'graph' && developerMode && (
          <div className="grid gap-4 lg:grid-cols-[320px,1fr]">
            <div className="rounded-2xl border border-border bg-card p-4">
              <input
                value={graphQuery}
                onChange={(event) => setGraphQuery(event.target.value)}
                placeholder="Search nodes..."
                className="mb-3 w-full rounded-xl border border-border bg-muted/30 px-3 py-2 text-sm text-foreground focus:outline-none"
              />
              <div className="max-h-[60vh] space-y-2 overflow-y-auto">
                {filteredNodes.map((node) => (
                  <button
                    key={node.id}
                    type="button"
                    onClick={() => setSelectedNodeId(node.id)}
                    className={`w-full rounded-xl border px-3 py-2 text-left transition-colors ${
                      selectedNode?.id === node.id ? 'border-primary bg-primary/10' : 'border-border bg-muted/20 hover:border-primary/40'
                    }`}
                  >
                    <p className="text-sm font-medium text-foreground">{node.label}</p>
                    <p className="text-xs text-muted-foreground">{node.type}</p>
                  </button>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-border bg-card p-5">
              {selectedNode ? (
                <>
                  <h3 className="text-lg font-semibold text-foreground">{selectedNode.label}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{selectedNode.type}</p>
                  <div className="mt-5 space-y-3">
                    {selectedEdges.map((edge) => (
                      <div key={edge.id} className="rounded-xl border border-border bg-muted/20 p-3">
                        <p className="text-sm text-foreground">{edge.type}</p>
                        <p className="mt-1 text-xs text-muted-foreground">{edge.source} → {edge.target}</p>
                      </div>
                    ))}
                    {selectedEdges.length === 0 ? <p className="text-sm text-muted-foreground">No connected edges for this node yet.</p> : null}
                  </div>
                </>
              ) : (
                <p className="text-sm text-muted-foreground">No graph nodes are available yet.</p>
              )}
            </div>
          </div>
        )}

        {activeTab === 'ops' && developerMode && (
          <div className="space-y-4">
            <section className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-sm font-semibold text-foreground">Ingestion Status</h3>
              <p className="mt-2 text-sm text-muted-foreground">{ingestionStatus?.message || 'No ingestion status available.'}</p>
              <p className="mt-2 text-xs text-muted-foreground">State: {ingestionStatus?.state || 'unknown'} • Changed sources: {ingestionStatus?.changed_sources ?? 'n/a'}</p>
            </section>
            <section className="rounded-2xl border border-border bg-card p-5">
              <h3 className="text-sm font-semibold text-foreground">Evaluation Summary</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                {evaluationStatus?.state === 'running'
                  ? 'Evaluation running...'
                  : evaluationSummary?.message || 'No evaluation summary available.'}
              </p>
              {evaluationStatus?.state === 'running' ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  Progress: {evaluationStatus?.progress_percent || 0}% • {evaluationStatus?.message || 'Processing evaluation'}
                </p>
              ) : null}
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {Object.entries(evaluationSummary?.metrics || {}).map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-border bg-muted/20 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">{key}</p>
                    <p className="mt-1 text-sm font-medium text-foreground">{String(value)}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {Object.entries(evaluationMetrics?.metrics || {}).map(([key, value]) => (
                  <div key={key} className="rounded-xl border border-border bg-muted/20 p-3">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">{key}</p>
                    <p className="mt-1 text-sm font-medium text-foreground">{String(value)}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex gap-3">
                <button
                  type="button"
                  onClick={runEvaluation}
                  disabled={evaluationStatus?.state === 'running'}
                  className="rounded-lg bg-primary/10 px-3 py-2 text-xs font-medium text-primary transition-colors hover:bg-primary/20"
                >
                  {evaluationStatus?.state === 'running' ? 'Evaluation running...' : 'Run RAGAS'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowEditor(true)}
                  className="rounded-lg bg-muted px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-muted/80"
                >
                  Open Turtle Editor
                </button>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-foreground">{value}</p>
    </div>
  );
}

function TwoColumnSection({ leftTitle, leftItems, rightTitle, rightItems }: { leftTitle: string; leftItems: string[]; rightTitle: string; rightItems: string[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ListCard title={leftTitle} items={leftItems} />
      <ListCard title={rightTitle} items={rightItems} />
    </div>
  );
}

function ListCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div key={item} className="rounded-xl border border-border bg-muted/20 p-3 text-sm text-foreground">{item}</div>
        ))}
        {items.length === 0 ? <p className="text-sm text-muted-foreground">No entries available yet.</p> : null}
      </div>
    </div>
  );
}

function CardGrid({ items, titleKey, subtitleKey, metaKey }: { items: Array<any>; titleKey: string; subtitleKey?: string; metaKey?: string }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <div key={item.id || item[titleKey]} className="rounded-2xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground">{item[titleKey]}</h3>
          {subtitleKey ? <p className="mt-2 text-sm leading-7 text-muted-foreground">{item[subtitleKey]}</p> : null}
          {metaKey && item[metaKey] ? (
            <p className="mt-4 text-xs text-muted-foreground">
              {Array.isArray(item[metaKey]) ? item[metaKey].join(', ') : item[metaKey]}
            </p>
          ) : null}
        </div>
      ))}
      {items.length === 0 ? <p className="text-sm text-muted-foreground">No entries available yet.</p> : null}
    </div>
  );
}

function FaqList({ items }: { items: Array<any> }) {
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.id} className="rounded-2xl border border-border bg-card p-5">
          <h3 className="text-sm font-semibold text-foreground">{item.question}</h3>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">{item.answer}</p>
        </div>
      ))}
      {items.length === 0 ? <p className="text-sm text-muted-foreground">No FAQs available yet.</p> : null}
    </div>
  );
}
