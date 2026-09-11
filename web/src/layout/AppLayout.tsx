import { useState, type ReactNode } from "react";
import { AppHeader } from "../components/AppHeader";
import { Sidebar } from "../components/Sidebar";
import { MenuIcon } from "../lib/icons";

interface AppLayoutProps {
  children: ReactNode;
}

// Shared shell for every authenticated page (Library, Boards, one Board) --
// each page renders <AppLayout> itself rather than this being an
// Outlet-nesting route wrapper, so a page's main content is just its
// children, no extra prop-threading needed for the common chrome.
export function AppLayout({ children }: AppLayoutProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="app-shell">
      <AppHeader />
      <div className="app-body">
        <button
          type="button"
          className="app-mobile-nav-toggle btn btn-secondary btn-sm"
          onClick={() => setMobileNavOpen((open) => !open)}
          aria-label={mobileNavOpen ? "Hide navigation" : "Show navigation"}
          aria-expanded={mobileNavOpen}
        >
          <MenuIcon size={16} />
          Menu
        </button>
        <Sidebar className={mobileNavOpen ? "mobile-open" : undefined} />
        <main className="app-main">{children}</main>
      </div>
    </div>
  );
}
