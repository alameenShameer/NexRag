import { Network, X } from 'lucide-react';

export function GraphViewDrawer({
  open,
  onClose,
  graphView,
  title,
}: {
  open: boolean;
  onClose: () => void;
  graphView?: { nodes?: Array<any>; edges?: Array<any> } | null;
  title?: string;
}) {
  if (!open) {
    return null;
  }

  const nodes = graphView?.nodes || [];
  const edges = graphView?.edges || [];

  return (
    <div className="fixed inset-0 z-50 flex bg-black/45">
      <button type="button" className="flex-1 cursor-default" onClick={onClose} aria-label="Close graph view" />
      <div className="flex h-full w-full max-w-[420px] flex-col border-l border-border bg-card shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Knowledge Graph View</p>
            <h3 className="mt-1 text-sm font-semibold text-foreground">{title || 'Answer Graph'}</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <div className="rounded-2xl border border-border bg-muted/20 p-4">
            <div className="flex items-center gap-2 text-foreground">
              <Network className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Focused graph snapshot</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              This view only shows the answer-relevant nodes and relationships surfaced during KG reasoning.
            </p>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-border/70 bg-background/50 p-3">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Nodes</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{nodes.length}</p>
              </div>
              <div className="rounded-xl border border-border/70 bg-background/50 p-3">
                <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Edges</p>
                <p className="mt-1 text-lg font-semibold text-foreground">{edges.length}</p>
              </div>
            </div>
          </div>

          <section className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Nodes</p>
            {nodes.length === 0 ? (
              <div className="rounded-xl border border-border bg-muted/20 p-4 text-xs text-muted-foreground">
                No answer-specific graph nodes were selected for this response.
              </div>
            ) : (
              nodes.map((node) => (
                <div key={node.id} className="rounded-xl border border-border bg-muted/20 p-3">
                  <p className="text-sm font-medium text-foreground">{node.label}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{node.type || 'entity'}</p>
                </div>
              ))
            )}
          </section>

          <section className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Relationships</p>
            {edges.length === 0 ? (
              <div className="rounded-xl border border-border bg-muted/20 p-4 text-xs text-muted-foreground">
                No traversed relationships are attached to this answer.
              </div>
            ) : (
              edges.map((edge) => (
                <div key={edge.id} className="rounded-xl border border-border bg-muted/20 p-3">
                  <p className="text-xs font-medium text-foreground">{edge.label || edge.type || 'related to'}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {edge.source} -&gt; {edge.target}
                  </p>
                </div>
              ))
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
