import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { HomePage } from "@/pages/HomePage";

const ComparisonPage = lazy(() => import("@/pages/ComparisonPage"));

function LoadingFallback() {
  return (
    <div className="flex h-dvh items-center justify-center bg-surface">
      <div className="text-center">
        <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-4 border-primary-light border-t-transparent" />
        <p className="text-text-secondary">Cargando...</p>
      </div>
    </div>
  );
}

function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/mesas-2022-2026" element={<ComparisonPage />} />
      </Routes>
    </Suspense>
  );
}

export default App;
