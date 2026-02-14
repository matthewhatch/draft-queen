import React, { useState, useEffect } from 'react'
import AlertList from './AlertList'
import AlertSummary from './AlertSummary'

export interface Alert {
  id: string
  position: string
  source: string
  severity: 'info' | 'warning' | 'critical'
  message: string
  details: string
  metric_name: string
  metric_value: number
  threshold: number
  quality_score: number
  created_at: string
  acknowledged_at?: string
  acknowledged_by?: string
  rule_id: string
}

interface QualityDashboardProps {
  apiBaseUrl?: string
}

export const QualityDashboard: React.FC<QualityDashboardProps> = ({ 
  apiBaseUrl = '/api' 
}) => {
  const [activeTab, setActiveTab] = useState<'alerts' | 'summary'>('alerts')
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleRefresh = () => {
    setRefreshTrigger(prev => prev + 1)
  }

  return (
    <div className="quality-dashboard space-y-6">
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 bg-white rounded-t-lg shadow-sm">
        <button
          onClick={() => setActiveTab('alerts')}
          className={`flex-1 px-6 py-4 font-medium transition-colors ${
            activeTab === 'alerts'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          🚨 Recent Alerts
        </button>
        <button
          onClick={() => setActiveTab('summary')}
          className={`flex-1 px-6 py-4 font-medium transition-colors ${
            activeTab === 'summary'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          📊 Summary
        </button>
        <button
          onClick={handleRefresh}
          className="px-6 py-4 text-gray-600 hover:text-gray-800 transition-colors"
          title="Refresh data"
        >
          🔄
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-b-lg shadow-sm p-6">
        {activeTab === 'alerts' ? (
          <AlertList
            apiBaseUrl={apiBaseUrl}
            onAcknowledge={handleRefresh}
            autoRefreshInterval={60}
          />
        ) : (
          <AlertSummary
            apiBaseUrl={apiBaseUrl}
          />
        )}
      </div>

      {/* Footer Info */}
      <div className="text-sm text-gray-500 text-center py-4">
        Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}
