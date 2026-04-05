import { ChevronDown, FileText, Network } from 'lucide-react';

export function SourcesAccordion({
  sources = [],
  kgFacts = [],
}: {
  sources?: Array<any>;
  kgFacts?: Array<any>;
}) {
  if (sources.length === 0 && kgFacts.length === 0) {
    return null;
  }

  return (
    <details className="group mt-4 rounded-2xl border border-border/70 bg-muted/20">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-foreground">
        <span>
          Sources & Grounding
          <span className="ml-2 text-xs text-muted-foreground">
            {sources.length} docs | {kgFacts.length} graph facts
          </span>
        </span>
        <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="space-y-3 border-t border-border/60 px-4 py-4">
        {kgFacts.length > 0 ? (
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Knowledge Graph Facts
            </p>
            {kgFacts.map((fact, index) => (
              <div key={`kg-${index}`} className="rounded-xl border border-border/70 bg-background/50 p-3">
                <div className="flex items-start gap-2">
                  <Network className="mt-0.5 h-4 w-4 flex-shrink-0 text-emerald-400" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-foreground">{fact.entity}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{fact.fact}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {sources.length > 0 ? (
          <div className="space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              Retrieved Documents
            </p>
            {sources.map((source, index) => (
              <div key={`source-${index}`} className="rounded-xl border border-border/70 bg-background/50 p-3">
                <div className="flex items-start gap-2">
                  <FileText className="mt-0.5 h-4 w-4 flex-shrink-0 text-primary" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-xs font-medium text-foreground">{source.title}</p>
                      <span className="text-[11px] text-muted-foreground">
                        {source.page ? `page ${source.page}` : 'document'} | {source.match_type}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{source.excerpt}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </details>
  );
}
