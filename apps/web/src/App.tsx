import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { Investigate } from './routes/Investigate';
import { Cases } from './routes/Cases';
import { Investigation } from './routes/Investigation';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Investigate />} />
          <Route path="cases" element={<Cases />} />
          <Route path="investigations/:id" element={<Investigation />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
