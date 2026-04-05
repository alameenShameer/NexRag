import { Activity, CheckCircle2, Database, FileText, Layers3, Network, Upload, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

type TabType = 'sources' | 'system-status';

export function IntelligencePanel({
  sources = [],
  kgFacts = [],
  status: externalStatus,
}: {
  sources?: Array<any>;
  kgFacts?: Array<any>;
  status?: any;
}) {
  const [activeTab, setActiveTab] = useState<TabType>('sources');
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    if (externalStatus) {
      setStatus(externalStatus);
      return;
    }

    const fetchStatus = async () => {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/status');
        setStatus(await res.json());
      } catch (error) {
        console.error('Status fetch failed', error);
      }
    };

    fetchStatus();
    const interval = window.setInterval(fetchStatus, 5000);
    return () => window.clearInterval(interval);
  }, [externalStatus]);

  const tabs = [
    { id: 'sources' as const, label: 'Sources', icon: FileText },
    { id: 'system-status' as const, label: 'System Status', icon: Activity },
  ];

  const checks = Object.values(status?.checks || {});
  const serviceChecks = checks.filter((check: any) => check.label !== 'Index version');
  const healthyChecks = serviceChecks.filter((check: any) => check.ok).length;
  const formatCheckDetail = (check: any) => {
    if (check.label === 'Knowledge Graph Ready' && status?.official_documents) {
      return `${check.detail} - ${status.official_documents} official docs`;
    }
    return check.detail;
  };

  const systemState = status?.state || 'loading';
  const stateLabel =
    systemState === 'ready' ? 'Ready to Answer' : systemState === 'error' ? 'Needs Attention' : 'Preparing Data';
  const stateBadgeClass =
    systemState === 'ready'
      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
      : systemState === 'error'
        ? 'border-rose-500/30 bg-rose-500/10 text-rose-300'
        : 'border-amber-500/30 bg-amber-500/10 text-amber-300';
  const summaryCards = [
    { label: 'LLM Model', value: status?.llm_model || 'Unavailable' },
    { label: 'Knowledge Docs', value: String(status?.official_documents || 0) },
    { label: 'Vector Chunks', value: String(status?.chunks || 0) },
    { label: 'Uploaded PDFs', value: String(status?.pdfs || 0) },
  ];

  return (
    <div className="w-[320px] h-full bg-card border-l border-border flex flex-col">
      <div className="flex border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative flex-1 px-3 py-3 text-xs font-medium transition-colors ${
              activeTab === tab.id ? 'text-primary' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <div className="flex items-center justify-center gap-1.5">
              <tab.icon className="h-3.5 w-3.5" />
              <span className="hidden xl:inline">{tab.label}</span>
            </div>
            {activeTab === tab.id ? <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" /> : null}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'sources' ? (
          <div className="space-y-3">
            <h3 className="mb-3 text-sm font-semibold text-foreground">Retrieved Sources</h3>

            {kgFacts.length === 0 && sources.length === 0 ? (
              <div className="rounded-lg border border-border bg-muted/20 p-4 text-xs leading-relaxed text-muted-foreground">
                No ranked sources are attached to the latest answer yet.
              </div>
            ) : null}

            {kgFacts.map((fact, index) => (
              <div key={`kg-${index}`} className="rounded-lg border border-border bg-muted/30 p-3">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <Network className="h-3.5 w-3.5 flex-shrink-0 text-emerald-400" />
                    <span className="truncate text-xs font-medium text-foreground">{fact.entity}</span>
                  </div>
                  <span className="text-xs font-medium text-emerald-400">Direct fact</span>
                </div>
                <p className="text-xs leading-relaxed text-muted-foreground">{fact.fact}</p>
              </div>
            ))}

            {sources.map((source, index) => (
              <div key={`source-${index}`} className="rounded-lg border border-border bg-muted/30 p-3">
                <div className="mb-2 flex items-start justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5 flex-shrink-0 text-primary" />
                    <span className="truncate text-xs font-medium text-foreground">{source.title}</span>
                  </div>
                  {source.page ? <span className="text-xs text-muted-foreground">Page {source.page}</span> : null}
                </div>
                <p className="mb-2 line-clamp-4 text-xs leading-relaxed text-muted-foreground">{source.excerpt}</p>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{source.match_type} match</span>
                  <span className="font-medium text-green-400">{Math.round((source.score || 0) * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <h3 className="mb-3 text-sm font-semibold text-foreground">System Status</h3>

            <div className="rounded-xl border border-border bg-muted/20 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    System Health
                  </p>
                  <h4 className="mt-2 text-sm font-semibold text-foreground">{stateLabel}</h4>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {status?.message || 'Status unavailable.'}
                  </p>
                </div>
                <span className={`rounded-full border px-2.5 py-1 text-[11px] font-medium ${stateBadgeClass}`}>
                  {systemState}
                </span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2">
                {summaryCards.map((card) => (
                  <div key={card.label} className="rounded-lg border border-border/70 bg-background/40 p-3">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{card.label}</p>
                    <p className="mt-2 break-words text-sm font-semibold text-foreground">{card.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-muted/20 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Layers3 className="h-4 w-4 text-primary" />
                  <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    Core Services
                  </h4>
                </div>
                <span className="text-[11px] text-muted-foreground">
                  {healthyChecks}/{serviceChecks.length} healthy
                </span>
              </div>

              <div className="space-y-2">
                {serviceChecks.map((check: any) => (
                  <div key={check.label} className="rounded-lg border border-border/70 bg-background/30 px-3 py-2.5">
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">
                        {check.ok ? (
                          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                        ) : (
                          <XCircle className="h-3.5 w-3.5 text-amber-400" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-foreground">{check.label}</p>
                        <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                          {formatCheckDetail(check)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-border bg-muted/20 p-4">
              <div className="mb-3 flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" />
                <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                  Index Version
                </h4>
              </div>
              <div className="rounded-lg border border-border/70 bg-background/40 px-3 py-2.5">
                <p className="break-all text-left font-mono text-[11px] leading-relaxed text-muted-foreground">
                  {status?.index_version || 'Unavailable'}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-muted/20 p-4">
              <div className="mb-3 flex items-center gap-2">
                <Upload className="h-4 w-4 text-primary" />
                <h4 className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Uploads</h4>
              </div>
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between rounded-lg border border-border/70 bg-background/30 px-3 py-2">
                  <span className="text-muted-foreground">Uploaded PDFs</span>
                  <span className="font-medium text-foreground">{status?.pdfs || 0}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border/70 bg-background/30 px-3 py-2">
                  <span className="text-muted-foreground">Indexed Uploads</span>
                  <span className="font-medium text-foreground">{status?.documents_indexed || 0}</span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border/70 bg-background/30 px-3 py-2">
                  <span className="text-muted-foreground">Uploads In Progress</span>
                  <span className="font-medium text-foreground">{status?.uploads_in_progress || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
