import { useState } from "react";
import { api } from "../api/client.js";
import { CURRENCIES, formatMinor } from "../lib/money.js";

export default function Transfer() {
  const [form, setForm] = useState({
    recipient_email: "",
    amount: "",
    from_currency: "USD",
    to_currency: "USD",
    reference: "",
  });
  const [message, setMessage] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    if (submitting) return;
    setMessage(null);
    const amount = Number(form.amount);
    if (!form.amount || Number.isNaN(amount) || amount <= 0) {
      setMessage({ type: "error", text: "Enter an amount greater than 0" });
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.transfer({ ...form, idempotency_key: crypto.randomUUID() });
      setMessage({
        type: "ok",
        text: `Sent ${formatMinor(res.debited_minor, res.from_currency)} → ${formatMinor(
          res.credited_minor,
          res.to_currency
        )} (rate ${res.fx_rate})`,
      });
      setForm({ ...form, amount: "", recipient_email: "" });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <h2>Transfer</h2>
      <form className="card" onSubmit={submit}>
        <div className="row">
          <div className="field">
            <label htmlFor="recipient_email">Recipient email</label>
            <input
              id="recipient_email"
              type="email"
              autoComplete="off"
              value={form.recipient_email}
              onChange={update("recipient_email")}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="transfer_amount">Amount</label>
            <input
              id="transfer_amount"
              inputMode="decimal"
              value={form.amount}
              onChange={update("amount")}
              placeholder="0.00"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="from_currency">From currency</label>
            <select
              id="from_currency"
              value={form.from_currency}
              onChange={update("from_currency")}
            >
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="to_currency">To currency</label>
            <select
              id="to_currency"
              value={form.to_currency}
              onChange={update("to_currency")}
            >
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="reference">Reference (optional)</label>
          <input id="reference" value={form.reference} onChange={update("reference")} />
        </div>
        <div style={{ marginTop: 16 }}>
          <button type="submit" disabled={submitting}>
            {submitting ? "Sending…" : "Send transfer"}
          </button>
        </div>
        {message && (
          <p className={message.type} role="alert" style={{ marginTop: 12 }}>
            {message.text}
          </p>
        )}
      </form>
    </>
  );
}
