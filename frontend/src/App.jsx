import Login from "./components/Login";
import Dashboard from "./pages/Dashboard";
import { useAuth } from "./services/auth";

export default function App() {
  const { token, login, logout } = useAuth();
  return token ? <Dashboard onLogout={logout} /> : <Login onAuth={login} />;
}
