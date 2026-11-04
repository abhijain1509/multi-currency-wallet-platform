// Single source of truth for currencies on the client. Mirrors the backend's
// supported_currencies / CURRENCY_DECIMALS so the UI can't silently drift.
export const CURRENCY_DECIMALS = {
  USD: 2,
  EUR: 2,
  GBP: 2,
  INR: 2,
  JPY: 0,
};

export const CURRENCIES = Object.keys(CURRENCY_DECIMALS);

function format(amount, currency) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
    }).format(amount);
  } catch {
    const decimals = CURRENCY_DECIMALS[currency] ?? 2;
    return `${amount.toFixed(decimals)} ${currency}`;
  }
}

// Format an integer minor-unit amount (e.g. cents) as a human currency string.
export function formatMinor(minor, currency) {
  const decimals = CURRENCY_DECIMALS[currency] ?? 2;
  return format(Number(minor) / 10 ** decimals, currency);
}

// Format a major-unit value (string or number, e.g. "100.00") as currency.
export function formatMajor(value, currency) {
  const amount = Number(value);
  if (Number.isNaN(amount)) return `${value} ${currency}`;
  return format(amount, currency);
}
