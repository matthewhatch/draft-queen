import { QualityDashboard } from './components/quality/QualityDashboard'
import './App.css'

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            📊 Quality Alert Dashboard
          </h1>
          <p className="text-gray-600 mt-2">
            Real-time prospect quality monitoring and alerts
          </p>
        </div>
      </header>
      
      <main className="max-w-7xl mx-auto px-4 py-8">
        <QualityDashboard />
      </main>
      
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-600 text-sm">
          <p>NFL Draft Queen • Quality Alert System • v1.0.0</p>
        </div>
      </footer>
    </div>
  )
}

export default App
