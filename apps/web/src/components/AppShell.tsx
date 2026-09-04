import { NavLink, Outlet } from 'react-router-dom';
import { DEV_ROLE } from '../lib/api';
import { useHealth } from '../lib/queries';

/**
 * Institutional application shell: a quiet top bar with the product wordmark,
 * primary navigation, and a dev role indicator. Branding is restrained
 * (DESIGN-SYSTEM.md §10) — no gradients, glass, or flourishes.
 */
export function AppShell() {
  const health = useHealth();

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <header className="topbar">
        <div className="topbar__inner">
          <div className="topbar__brand">
            <span className="topbar__wordmark">ARIE</span>
            <span className="topbar__product">Sentinel</span>
            <span className="topbar__tagline">Counterparty Integrity</span>
          </div>

          <nav className="topbar__nav" aria-label="Primary">
            <NavLink
              to="/"
              end
              className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
            >
              Investigate
            </NavLink>
            <NavLink
              to="/cases"
              className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
            >
              Cases
            </NavLink>
          </nav>

          <div className="topbar__meta">
            <span className="role-indicator" title="Development role sent with API calls">
              <span className="role-indicator__label">Role</span>
              <span className="role-indicator__value">{DEV_ROLE}</span>
            </span>
            <span
              className={`service-dot service-dot--${health.isSuccess ? 'ok' : health.isError ? 'down' : 'unknown'}`}
            >
              <span className="service-dot__mark" aria-hidden="true">
                {health.isSuccess ? '●' : health.isError ? '▲' : '○'}
              </span>
              <span className="service-dot__text">
                {health.isSuccess
                  ? `API v${health.data.version}`
                  : health.isError
                    ? 'API unreachable'
                    : 'API…'}
              </span>
            </span>
          </div>
        </div>
      </header>

      <main id="main" className="app-main" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
