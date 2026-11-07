import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { BookIcon, ChevronDownIcon, PlusIcon } from "../lib/icons";
import { AppearanceDialog } from "./AppearanceDialog";

// Global header, shared by every authenticated page via AppLayout. "Add
// Resource" always routes to Library with navigation state rather than
// needing a page-specific callback threaded down through AppLayout --
// same mechanism ProtectedRoute already uses for its own `from` state, not
// a new pattern.
export function AppHeader() {
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [appearanceOpen, setAppearanceOpen] = useState(false);
  const userButtonRef = useRef<HTMLButtonElement>(null);

  const firstName = currentUser?.first_name ?? null;
  const avatarLetter = (firstName ?? currentUser?.email ?? "?").charAt(0).toUpperCase();

  return (
    <header className="app-header">
      <Link to="/" className="app-header-brand">
        <BookIcon className="app-header-brand-icon" size={22} />
        <span className="app-header-brand-text">
          <span className="app-header-title">Study Hub</span>
          <span className="app-header-subtitle">Curate. Organize. Share what you're learning.</span>
        </span>
      </Link>

      <div className="app-header-actions">
        <button
          className="btn btn-primary"
          onClick={() => navigate("/", { state: { openAddDialog: true } })}
        >
          <PlusIcon size={16} />
          <span className="app-header-add-label">Add Resource</span>
        </button>

        <div
          className="app-header-user"
          onKeyDown={(event) => {
            // Escape closes the menu and puts focus back on the avatar button
            if (event.key === "Escape" && menuOpen) {
              setMenuOpen(false);
              userButtonRef.current?.focus();
            }
          }}
        >
          <button
            className="app-header-user-button"
            ref={userButtonRef}
            onClick={() => setMenuOpen((open) => !open)}
            aria-haspopup="true"
            aria-expanded={menuOpen}
          >
            <span className="avatar">{avatarLetter}</span>
            {firstName ?? "Welcome back"}
            <ChevronDownIcon size={14} />
          </button>
          {menuOpen && (
            <div className="app-header-menu" role="menu">
              <button
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  setAppearanceOpen(true);
                }}
              >
                Appearance
              </button>
              <button role="menuitem" onClick={() => logout()}>
                Log out
              </button>
            </div>
          )}
        </div>
      </div>

      {appearanceOpen && (
        <AppearanceDialog
          onClose={() => {
            setAppearanceOpen(false);
            userButtonRef.current?.focus(); // back to where the person was
          }}
        />
      )}
    </header>
  );
}
