import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { CURRENCIES, formatMajor } from "../lib/money.js";

export default function Dashboard() {
  const [wallets, setWallets] = useState([]);
  const [rates, setRates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    wallet_currency: "USD",
    amount: "",
    amount_currency: "USD",
  });
  const [message, setMessage] = useState(null);

  async function load() {
    try {
      const [w, r] = await Promise.all([api.listWallets(), api.rates()]);
      setWallets(w);
      setRates(r);
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function operate(kind) {
    if (submitting) return;
    setMessage(null);
    const amount = Number(form.amount);
    if (!form.amount || Number.isNaN(amount) || amount <= 0) {
      setMessage({ type: "error", text: "Enter an amount greater than 0" });
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        wallet_currency: form.wallet_currency,
        amount: form.amount,
        amount_currency: form.amount_currency,
        idempotency_key: crypto.randomUUID(),
      };
      await (kind === "credit" ? api.credit(payload) : api.debit(payload));
      setMessage({ type: "ok", text: `${kind === "credit" ? "Credit" : "Debit"} successful` });
      setForm({ ...form, amount: "" });
      load();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <h2>Wallets</h2>
      <div className="card">
        {loading ? (
          <p className="badge">Loading…</p>
        ) : wallets.length === 0 ? (
          <p className="badge">No wallets yet — credit one below.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Currency</th>
                  <th>Balance</th>
                </tr>
              </thead>
              <tbody>
                {wallets.map((w) => (
                  <tr key={w.id}>
                    <td>{w.currency}</td>
                    <td>{formatMajor(w.balance, w.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <h3>Credit / Debit</h3>
        <div className="row">
          <div className="field">
            <label htmlFor="wallet_currency">Wallet currency</label>
            <select
              id="wallet_currency"
              value={form.wallet_currency}
              onChange={update("wallet_currency")}
            >
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="amount">Amount</label>
            <input
              id="amount"
              inputMode="decimal"
              value={form.amount}
              onChange={update("amount")}
              placeholder="0.00"
            />
          </div>
          <div className="field">
            <label htmlFor="amount_currency">Amount currency</label>
            <select
              id="amount_currency"
              value={form.amount_currency}
              onChange={update("amount_currency")}
            >
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <button onClick={() => operate("credit")} disabled={submitting}>
            {submitting ? "Working…" : "Credit"}
          </button>
          <button
            className="secondary"
            onClick={() => operate("debit")}
            disabled={submitting}
          >
            {submitting ? "Working…" : "Debit"}
          </button>
        </div>
        {message && (
          <p className={message.type} role="alert">
            {message.text}
          </p>
        )}
      </div>

      <div className="card">
        <h3>Exchange rates (base USD)</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Pair</th>
                <th>Rate</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rates.map((r) => (
                <tr key={r.quote}>
                  <td>
                    {r.base} → {r.quote}
                  </td>
                  <td>{r.rate}</td>
                  <td>
                    <span className="badge">{r.stale ? "stale" : "fresh"}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
