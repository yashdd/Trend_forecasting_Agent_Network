import { BrowserRouter, Routes, Route } from "react-router-dom";
import SignalsFeed from "./pages/SignalsFeed";
import Dashboard from "./pages/Dashboard";
import TopicDeepDive from "./pages/TopicDeepDive";
import WeeklyReport from "./pages/WeeklyReport";
import AlertsPage from "./pages/Alerts";
import Navbar from "./components/Navbar";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen">
        <Navbar />

        <main className="max-w-7xl w-full mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<SignalsFeed />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/topics/:topicId" element={<TopicDeepDive />} />
            <Route path="/reports" element={<WeeklyReport />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
