import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Login from "./Login.jsx";

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

describe("Login", () => {
  it("renders the login form", () => {
    renderLogin();
    expect(screen.getByRole("heading", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  });

  it("switches to signup and shows the full name field", () => {
    renderLogin();
    fireEvent.click(screen.getByRole("button", { name: /sign up/i }));
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/default currency/i)).toBeInTheDocument();
  });
});
