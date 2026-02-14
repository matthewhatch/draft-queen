/**
 * QualityDashboard Page - Main quality alerts dashboard
 * 
 * Features:
 * - Alert summary statistics
 * - Filterable alert list
 * - Real-time updates
 * - Bulk operations
 * - Responsive design
 */

import React, { useState } from 'react';
import AlertSummary from '../components/quality/AlertSummary';
import AlertList from '../components/quality/AlertList';

const QualityDashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'summary' | 'alerts'>('alerts');
  const [refreshCount, setRefreshCount] = useState(0);

  const handleManualRefresh = () => {
    setRefreshCount(prev => prev + 1);
  };

  const apiBaseUrl = process.env.REACT_APP_API_URL || '/api';

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Quality Dashboard</h1>
              <p className="text-gray-600 text-sm mt-1">
                Monitor data quality metrics and alerts across all positions and sources
              </p>
            </div>
            <button
              onClick={handleManualRefresh}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 active:bg-blue-700 font-medium transition-colors flex items-center gap-2"
            >
              <span>🔄</span>
              Refresh
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-8">
            <button
              onClick={() => setActiveTab('alerts')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'alerts'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <span className="mr-2">🚨</span>Alerts
            </button>
            <button
              onClick={() => setActiveTab('summary')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === 'summary'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <span className="mr-2">📊</span>Summary
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {activeTab === 'alerts' && (
          <div className="space-y-6">
            <AlertList
              apiBaseUrl={apiBaseUrl}
              autoRefreshInterval={60}
              key={`alerts-${refreshCount}`}
            />
          </div>
        )}

        {activeTab === 'summary' && (
          <div className="space-y-6">
            <AlertSummary
              apiBaseUrl={apiBaseUrl}
              days={7}
              autoRefreshInterval={60}
              key={`summary-${refreshCount}`}
            />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="text-center text-sm text-gray-600">
            <p>
              Quality Dashboard • Last Updated: {new Date().toLocaleString()} • Auto-refresh every 60 seconds
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default QualityDashboard;
