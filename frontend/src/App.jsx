import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { api, clearSession, getUser } from "./api/client.js";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Transfer from "./pages/Transfer.jsx";
import History from "./pages/History.jsx";
import Profile from "./pages/Profile.jsx";
import { Link } from "react-router-dom";

function RequireAuth({ children }) {
  return getUser() ? children : <Navigate to="/login" replace />;
}

function Nav() {
  const navigate = useNavigate();
  const user = getUser();
  return (
    <nav>
      <Link to={user ? "/" : "/login"} className="brand">
        <span aria-hidden="true">💳</span> Multi-Currency Wallet
      </Link>
      {user && (
        <>
          <Link to="/">Wallets</Link>
          <Link to="/transfer">Transfer</Link>
          <Link to="/history">History</Link>
          <Link to="/profile">Profile</Link>
        </>
      )}
      <span className="spacer" />
      {user && (
        <>
          <span className="badge">{user.email}</span>
          <button
            className="secondary"
            onClick={async () => {
              try {
                await api.logout();
              } catch {
                // Ignore network errors; clear local state regardless.
              }
              clearSession();
              navigate("/login");
            }}
          >
            Logout
          </button>
        </>
      )}
    </nav>
  );
}

export default function App() {
  return (
    <>
      <Nav />
      <div className="container">
        <ErrorBoundary>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <RequireAuth>
                  <Dashboard />
                </RequireAuth>
              }
            />
            <Route
              path="/transfer"
              element={
                <RequireAuth>
                  <Transfer />
                </RequireAuth>
              }
            />
            <Route
              path="/history"
              element={
                <RequireAuth>
                  <History />
                </RequireAuth>
              }
            />
            <Route
              path="/profile"
              element={
                <RequireAuth>
                  <Profile />
                </RequireAuth>
              }
            />
          </Routes>
        </ErrorBoundary>
      </div>
    </>
  );
}
