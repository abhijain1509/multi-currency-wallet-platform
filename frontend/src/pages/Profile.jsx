import { useEffect, useState } from "react";
import { api, setSession } from "../api/client.js";
import { CURRENCIES } from "../lib/money.js";

export default function Profile() {
  const [form, setForm] = useState({
    full_name: "",
    photo_url: "",
    default_currency: "USD",
  });
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);

  async function load() {
    try {
      const me = await api.profile();
      setEmail(me.email);
      setForm({
        full_name: me.full_name ?? "",
        photo_url: me.photo_url ?? "",
        default_currency: me.default_currency ?? "USD",
      });
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

  async function handlePhotoUpload(e) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;
    setMessage(null);
    setUploading(true);
    try {
      const updated = await api.uploadPhoto(file);
      setForm((f) => ({ ...f, photo_url: updated.photo_url ?? "" }));
      setSession(updated);
      setMessage({ type: "ok", text: "Photo uploaded" });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setUploading(false);
    }
  }

  async function submit(e) {
    e.preventDefault();
    if (submitting) return;
    setMessage(null);
    setSubmitting(true);
    try {
      const updated = await api.updateProfile({
        full_name: form.full_name,
        photo_url: form.photo_url || null,
        default_currency: form.default_currency,
      });
      // Keep the locally cached display info in sync with the saved profile.
      setSession(updated);
      setMessage({ type: "ok", text: "Profile updated" });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="card">
        <p className="badge">Loading…</p>
      </div>
    );
  }

  const initials = (form.full_name || email || "?").trim().charAt(0).toUpperCase();

  return (
    <>
      <h2>Profile</h2>
      <form className="card" onSubmit={submit}>
        <div className="profile-head">
          {form.photo_url ? (
            <img
              className="avatar"
              src={form.photo_url}
              alt="Profile"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          ) : (
            <div className="avatar avatar-fallback">{initials}</div>
          )}
          <div>
            <div style={{ fontWeight: 600 }}>{form.full_name || "—"}</div>
            <div className="badge">{email}</div>
            <div style={{ marginTop: 8 }}>
              <label htmlFor="photo_file" className="upload-btn">
                {uploading ? "Uploading…" : "Upload photo"}
              </label>
              <input
                id="photo_file"
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                onChange={handlePhotoUpload}
                disabled={uploading}
                style={{ display: "none" }}
              />
            </div>
          </div>
        </div>

        <div className="field" style={{ marginTop: 16 }}>
          <label htmlFor="full_name">Full name</label>
          <input id="full_name" value={form.full_name} onChange={update("full_name")} required />
        </div>

        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="photo_url">Photo URL</label>
          <input
            id="photo_url"
            type="url"
            placeholder="https://… or upload above"
            value={form.photo_url}
            onChange={update("photo_url")}
          />
        </div>

        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="default_currency">Default currency</label>
          <select
            id="default_currency"
            value={form.default_currency}
            onChange={update("default_currency")}
          >
            {CURRENCIES.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </div>

        <div style={{ marginTop: 16 }}>
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving…" : "Save changes"}
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
