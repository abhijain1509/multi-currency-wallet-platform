import { describe, expect, it } from "vitest";
import { CURRENCIES, formatMajor, formatMinor } from "./money.js";

describe("money formatting", () => {
  it("formats minor units for 2-decimal currencies", () => {
    expect(formatMinor(1000, "USD")).toBe("$10.00");
  });

  it("formats minor units for 0-decimal currencies", () => {
    // 1500 JPY minor units == 1500 yen (no division).
    expect(formatMinor(1500, "JPY")).toBe("¥1,500");
  });

  it("renders negative amounts with a sign", () => {
    expect(formatMinor(-2500, "USD")).toBe("-$25.00");
  });

  it("formats major-unit strings from the API", () => {
    expect(formatMajor("100.00", "USD")).toBe("$100.00");
  });

  it("exposes the supported currency list", () => {
    expect(CURRENCIES).toContain("USD");
    expect(CURRENCIES).toContain("JPY");
  });
});
