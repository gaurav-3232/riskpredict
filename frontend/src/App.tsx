import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Datasets from './pages/Datasets';
import Experiments from './pages/Experiments';
import Predict from './pages/Predict';

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-64 p-8">
          <div className="max-w-6xl mx-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/datasets" element={<Datasets />} />
              <Route path="/experiments" element={<Experiments />} />
              <Route path="/predict" element={<Predict />} />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  );
}
