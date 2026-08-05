import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/**
 * Persistent nav for logged-in app pages only.
 * Do not render on Landing / Login / Signup.
 */
export default function NavBar() {
  const { user, logout } = useAuth();

  return (
    <nav className="app-nav" aria-label="Main">
      <NavLink to="/swipe" className="app-nav__brand" end={false}>
        The Edit
      </NavLink>

      <div className="app-nav__links">
        <NavLink
          to="/swipe"
          className={({ isActive }) =>
            isActive ? "app-nav__link app-nav__link--active" : "app-nav__link"
          }
        >
          Swipe
        </NavLink>
        <NavLink
          to="/saved"
          className={({ isActive }) =>
            isActive ? "app-nav__link app-nav__link--active" : "app-nav__link"
          }
        >
          Saved
        </NavLink>
        <NavLink
          to="/profile"
          className={({ isActive }) =>
            isActive ? "app-nav__link app-nav__link--active" : "app-nav__link"
          }
        >
          Profile
        </NavLink>
      </div>

      <div className="app-nav__right">
        <span className="app-nav__email">{user?.email}</span>
        <button type="button" className="text-link" onClick={logout}>
          Log out
        </button>
      </div>
    </nav>
  );
}
