import { useQuery } from '@tanstack/react-query';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { FolderKanban, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { getHealth } from '@/services/api';

export function AppLayout() {
  const location = useLocation();
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 20_000,
    retry: 1,
  });
  const isCaseRoute = location.pathname.startsWith('/cases/');
  const healthy = healthQuery.data?.status === 'healthy';

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand-lockup" aria-label="Sentinel investigations">
          <span className="brand-mark"><ShieldCheck className="h-[18px] w-[18px]" /></span>
          <span className="brand-copy">
            <span className="brand-name">Sentinel</span>
            <span className="brand-caption">INVESTIGATIONS</span>
          </span>
        </NavLink>
        <div className="sidebar-section-label">Workspace</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          <NavLink to="/" end className={({ isActive }) => `sidebar-link ${isActive || isCaseRoute ? 'active' : ''}`}>
            <FolderKanban className="h-4 w-4" />
            <span>Cases</span>
          </NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="health-row">
            <span className={`health-indicator ${healthQuery.isError ? 'offline' : healthy ? 'online' : 'checking'}`} />
            <div className="min-w-0">
              <div className="health-label">Backend API</div>
              <div className="health-value">
                {healthQuery.isLoading ? 'Checking connection' : healthQuery.isError ? 'Unavailable' : healthQuery.data?.status ?? 'Connected'}
              </div>
            </div>
            {healthQuery.isSuccess && <Badge variant={healthy ? 'success' : 'warning'}>{healthy ? 'Online' : 'Degraded'}</Badge>}
          </div>
        </div>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div className="topbar-breadcrumb">
            <span>Sentinel</span>
            <span className="breadcrumb-divider">/</span>
            <strong>{isCaseRoute ? 'Case workspace' : 'Cases'}</strong>
          </div>
          <div className="topbar-right">
            <span className={`health-indicator ${healthQuery.isError ? 'offline' : healthy ? 'online' : 'checking'}`} />
            <span>{healthQuery.isError ? 'API unavailable' : healthQuery.isLoading ? 'Connecting' : healthy ? 'API connected' : 'API status'}</span>
          </div>
        </header>
        <main className="page-content"><Outlet /></main>
      </div>
    </div>
  );
}
