import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from '@/layouts/AppLayout';

const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage })),
);
const CasePage = lazy(() =>
  import('@/pages/CasePage').then((module) => ({ default: module.CasePage })),
);

function RouteFallback() {
  return (
    <div className="page-stack" role="status" aria-label="Loading page">
      <div className="h-7 w-48 animate-pulse rounded bg-muted" />
      <div className="h-4 w-72 max-w-full animate-pulse rounded bg-muted" />
      <div className="h-48 w-full animate-pulse rounded-xl border bg-muted/50" />
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route
          index
          element={
            <Suspense fallback={<RouteFallback />}>
              <DashboardPage />
            </Suspense>
          }
        />
        <Route path="cases/:caseId" element={<Navigate to="overview" replace />} />
        <Route
          path="cases/:caseId/:section"
          element={
            <Suspense fallback={<RouteFallback />}>
              <CasePage />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
