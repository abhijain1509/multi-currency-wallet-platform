import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { CURRENCIES as SUPPORTED, formatMinor } from "../lib/money.js";

const TYPES = ["", "credit", "debit", "transfer_in", "transfer_out"];
const CURRENCIES = ["", ...SUPPORTED];
const PAGE_SIZE = 10;

export default function History() {
  const [filters, setFilters] = useState({ type: "", currency: "" });
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    setLoading(true);
    const params = new URLSearchParams({ limit: PAGE_SIZE, offset });
    if (filters.type) params.set("type", filters.type);
    if (filters.currency) params.set("currency", filters.currency);
    try {
      setPage(await api.transactions(`?${params.toString()}`));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [offset, filters]);

  const update = (key) => (e) => {
    setOffset(0);
    setFilters({ ...filters, [key]: e.target.value });
  };

  const maxOffset = Math.max(0, page.total - PAGE_SIZE);

  return (
    <>
      <h2>Transaction history</h2>
      <div className="card">
        <div className="row">
          <div className="field">
            <label htmlFor="filter_type">Type</label>
            <select id="filter_type" value={filters.type} onChange={update("type")}>
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t || "all"}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="filter_currency">Currency</label>
            <select
              id="filter_currency"
              value={filters.currency}
              onChange={update("currency")}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>
                  {c || "all"}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        {error && <p className="error" role="alert">{error}</p>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Amount</th>
                <th>FX</th>
              </tr>
            </thead>
            <tbody>
              {page.items.map((t) => (
                <tr key={t.id}>
                  <td>{new Date(t.created_at).toLocaleString()}</td>
                  <td>
                    <span className="badge">{t.type}</span>
                  </td>
                  <td>{formatMinor(t.amount_minor, t.currency)}</td>
                  <td>{t.fx_rate ?? "—"}</td>
                </tr>
              ))}
              {loading && (
                <tr>
                  <td colSpan="4">Loading…</td>
                </tr>
              )}
              {!loading && page.items.length === 0 && (
                <tr>
                  <td colSpan="4">No transactions.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="row" style={{ marginTop: 12, justifyContent: "space-between" }}>
          <span className="badge">
            {page.total} total · showing {offset + 1}-{Math.min(offset + PAGE_SIZE, page.total)}
          </span>
          <div className="row">
            <button
              className="secondary"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Prev
            </button>
            <button
              className="secondary"
              disabled={offset >= maxOffset}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
