import { useLocation, useNavigate } from "react-router-dom";
import { BookIcon, BoardsIcon, ChecklistIcon } from "../lib/icons";

interface SidebarProps {
  className?: string;
}

// "Library", "Boards", and "Plans" are real routes; "Sources > Browser
// Bookmarks" isn't (redesign spec section 8 explicitly allows this) -- it
// navigates to Library and scrolls to that section instead, via the same
// navigation-state mechanism AppHeader's "Add Resource" uses.
export function Sidebar({ className }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();

  const isLibrary = location.pathname === "/";
  const isBoards = location.pathname.startsWith("/board");
  const isPlans = location.pathname.startsWith("/plans");

  return (
    <nav className={`app-sidebar${className ? ` ${className}` : ""}`}>
      <div className="app-sidebar-section">
        <button
          className={`app-sidebar-link${isLibrary ? " active" : ""}`}
          onClick={() => navigate("/")}
        >
          <BookIcon size={16} />
          Library
        </button>
        <button
          className={`app-sidebar-link${isPlans ? " active" : ""}`}
          onClick={() => navigate("/plans")}
        >
          <ChecklistIcon size={16} />
          Plans
        </button>
        <button
          className={`app-sidebar-link${isBoards ? " active" : ""}`}
          onClick={() => navigate("/boards")}
        >
          <BoardsIcon size={16} />
          Boards
        </button>
      </div>

      <div className="app-sidebar-section">
        <div className="app-sidebar-label">Sources</div>
        <button
          className="app-sidebar-link"
          onClick={() => navigate("/", { state: { scrollTo: "browser-bookmarks" } })}
        >
          Browser Bookmarks
        </button>
      </div>
    </nav>
  );
}
