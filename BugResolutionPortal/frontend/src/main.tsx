import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import type { FormEvent } from "react";
import "./styles.css";

type Issue = {
  issue_id: string;
  title: string;
  priority_label: string;
  status_label: string;
  priority: string;
  status: string;
};

type Dashboard = {
  stats: { open: number; in_progress: number; resolved: number; critical: number; total: number };
  recent_issues: Issue[];
  my_issues: Issue[];
};

type QueryResult = {
  issue_id: string;
  title: string;
  priority_label: string;
  status_label: string;
  priority: string;
};

const cards = [
  ["open", "Open", "Waiting for ownership"],
  ["in_progress", "In progress", "Currently being fixed"],
  ["resolved", "Resolved", "Ready for verification"],
  ["critical", "Critical", "Needs attention first"],
] as const;

function App() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [queryError, setQueryError] = useState("");
  const [queryResults, setQueryResults] = useState<QueryResult[]>([]);
  const [queryLoading, setQueryLoading] = useState(false);

  useEffect(() => {
    fetch("/api/dashboard/", { credentials: "include" })
      .then(async (response) => {
        const contentType = response.headers.get("content-type") ?? "";
        if (!response.ok) {
          throw new Error(
            response.status === 401
              ? "Please sign in through the Django app first."
              : `Dashboard request failed (${response.status}).`,
          );
        }
        if (!contentType.includes("application/json")) {
          throw new Error("The dashboard returned an unexpected response.");
        }
        return response.json() as Promise<Dashboard>;
      })
      .then(setDashboard)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  if (error) return <main className="shell"><div className="error">{error}</div><a href="http://127.0.0.1:8000/login/">Sign in</a></main>;
  if (!dashboard) return <main className="shell"><p className="muted">Loading your workspace...</p></main>;

  const askQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!question.trim()) return;
    setQueryLoading(true);
    setQueryError("");
    try {
      const response = await fetch(`/api/issues/query/?q=${encodeURIComponent(question)}`, { credentials: "include" });
      const payload = await response.json() as { issues?: QueryResult[]; error?: string };
      if (!response.ok) throw new Error(payload.error ?? "Could not answer that question.");
      setQueryResults(payload.issues ?? []);
    } catch (reason) {
      setQueryError(reason instanceof Error ? reason.message : "Could not answer that question.");
      setQueryResults([]);
    } finally {
      setQueryLoading(false);
    }
  };

  return (
    <main className="shell">
      <header className="hero">
        <div><p className="eyebrow">BUGRESOLUTIONPORTAL</p><h1>Good morning. Here is your delivery pulse.</h1><p className="muted">A focused view of quality, ownership, and work in motion.</p></div>
        <a className="button" href="http://127.0.0.1:8000/issues/new/">Report issue</a>
      </header>
      <section className="metrics">
        {cards.map(([key, label, note]) => <article className={`metric metric--${key}`} key={key}><span>{label}</span><strong>{dashboard.stats[key]}</strong><small>{note}</small></article>)}
      </section>
      <section className="ask panel">
        <div className="panel__header">
          <div><p className="eyebrow">AI ISSUE ASSISTANT</p><h2>Ask a question about your bugs</h2></div>
        </div>
        <form className="ask__form" onSubmit={askQuestion}>
          <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Which critical issues are still open?" aria-label="Ask about issues" />
          <button className="button" type="submit" disabled={queryLoading}>{queryLoading ? "Thinking..." : "Ask"}</button>
        </form>
        <p className="ask__hint">Try: “Show high-priority login issues” or “Which bugs are in progress?”</p>
        {queryError && <div className="error">{queryError}</div>}
        {queryResults.length > 0 && <ul className="ask__results">{queryResults.map((issue) => <li key={issue.issue_id}><div><b>{issue.issue_id}</b><span>{issue.title}</span></div><aside><em className={`pill pill--${issue.priority.toLowerCase()}`}>{issue.priority_label}</em><em className="pill pill--neutral">{issue.status_label}</em></aside></li>)}</ul>}
        {!queryLoading && !queryError && question && queryResults.length === 0 && <p className="muted">No matching issues found.</p>}
      </section>
      <section className="columns">
        <IssuePanel title="Latest reports" issues={dashboard.recent_issues} total={dashboard.stats.total} />
        <IssuePanel title="Assigned to you" issues={dashboard.my_issues} total={dashboard.my_issues.length} />
      </section>
    </main>
  );
}

function IssuePanel({ title, issues, total }: { title: string; issues: Issue[]; total: number }) {
  return <section className="panel"><div className="panel__header"><div><p className="eyebrow">WORK QUEUE</p><h2>{title}</h2></div><span className="count">{total}</span></div>{issues.length === 0 ? <p className="muted">Nothing to show here.</p> : <ul>{issues.map((issue) => <li key={issue.issue_id}><div><b>{issue.issue_id}</b><span>{issue.title}</span></div><aside><em className={`pill pill--${issue.priority.toLowerCase()}`}>{issue.priority_label}</em><em className="pill pill--neutral">{issue.status_label}</em></aside></li>)}</ul>}</section>;
}

import { useEffect, useState } from "react";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
