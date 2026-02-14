/**
 * AlertSummary Component - Display alert statistics and trends
 * 
 * Features:
 * - Alert counts by position
 * - Alert counts by source
 * - Alert counts by type
 * - Critical alerts highlighting
 * - Responsive grid layout
 */

import React, { useState, useEffect } from 'react';

interface AlertStats {
  total_alerts: number;
  unacknowledged_critical: number;
  unacknowledged_warning: number;
  unacknowledged_info: number;
  by_position: Record<string, number>;
  by_source: Record<string, number>;
  by_type: Record<string, number>;
  critical_positions: string[];
  critical_sources: string[];
  oldest_unacknowledged_alert_age_hours?: number;
}

interface AlertSummaryProps {
  apiBaseUrl?: string;
  days?: number;
  autoRefreshInterval?: number;
}

const AlertSummary: React.FC<AlertSummaryProps> = ({
  apiBaseUrl = '/api',
  days = 7,
  autoRefreshInterval = 60,
}) => {
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/quality/alerts/summary?days=${days}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch alert summary: ${response.statusText}`);
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [days]);

  useEffect(() => {
    if (autoRefreshInterval <= 0) return;

    const interval = setInterval(fetchStats, autoRefreshInterval * 1000);
    return () => clearInterval(interval);
  }, [autoRefreshInterval]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-2">⏳</div>
          <p className="text-gray-600">Loading summary...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-red-50 border border-red-300 text-red-800 p-4 rounded">
        <h3 className="font-semibold mb-1">Error Loading Summary</h3>
        <p className="text-sm">{error || 'Unknown error'}</p>
        <button
          onClick={fetchStats}
          className="mt-3 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 text-sm font-medium"
        >
          Retry
        </button>
      </div>
    );
  }

  const unacknowledgedTotal =
    stats.unacknowledged_critical + stats.unacknowledged_warning + stats.unacknowledged_info;

  const formatAge = (hours?: number) => {
    if (!hours) return 'N/A';
    if (hours < 1) return '< 1 hour';
    if (hours < 24) return `${Math.floor(hours)} hours`;
    return `${Math.floor(hours / 24)} days`;
  };

  return (
    <div className="space-y-6">
      {/* Overall Statistics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatBox
          label="Total Alerts"
          value={stats.total_alerts}
          color="blue"
        />
        <StatBox
          label="Unacknowledged"
          value={unacknowledgedTotal}
          color={unacknowledgedTotal > 0 ? 'red' : 'green'}
        />
        <StatBox
          label="Critical (Pending)"
          value={stats.unacknowledged_critical}
          color="red"
          highlight
        />
        <StatBox
          label="Oldest Alert"
          value={formatAge(stats.oldest_unacknowledged_alert_age_hours)}
          color="orange"
        />
      </div>

      {/* Unacknowledged by Severity */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Pending Alerts by Severity</h3>
        <div className="grid grid-cols-3 gap-4">
          <SeverityBox
            icon="🔴"
            label="CRITICAL"
            count={stats.unacknowledged_critical}
            color="red"
          />
          <SeverityBox
            icon="🟡"
            label="WARNING"
            count={stats.unacknowledged_warning}
            color="yellow"
          />
          <SeverityBox
            icon="ℹ️"
            label="INFO"
            count={stats.unacknowledged_info}
            color="blue"
          />
        </div>
      </div>

      {/* Alerts by Position */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">
          Alerts by Position
          {stats.critical_positions.length > 0 && (
            <span className="ml-2 text-red-600 text-sm font-normal">
              ⚠️ Critical: {stats.critical_positions.join(', ')}
            </span>
          )}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(stats.by_position).length === 0 ? (
            <p className="text-gray-500 text-sm">No alerts by position</p>
          ) : (
            Object.entries(stats.by_position)
              .sort((a, b) => b[1] - a[1])
              .map(([position, count]) => (
                <PositionBox
                  key={position}
                  position={position}
                  count={count}
                  hasCritical={stats.critical_positions.includes(position)}
                />
              ))
          )}
        </div>
      </div>

      {/* Alerts by Source */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">
          Alerts by Source
          {stats.critical_sources.length > 0 && (
            <span className="ml-2 text-red-600 text-sm font-normal">
              ⚠️ Critical: {stats.critical_sources.map(s => s.toUpperCase()).join(', ')}
            </span>
          )}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(stats.by_source).length === 0 ? (
            <p className="text-gray-500 text-sm">No alerts by source</p>
          ) : (
            Object.entries(stats.by_source)
              .sort((a, b) => b[1] - a[1])
              .map(([source, count]) => (
                <SourceBox
                  key={source}
                  source={source}
                  count={count}
                  hasCritical={stats.critical_sources.includes(source)}
                />
              ))
          )}
        </div>
      </div>

      {/* Alerts by Type */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Alerts by Type</h3>
        <div className="space-y-2">
          {Object.entries(stats.by_type).length === 0 ? (
            <p className="text-gray-500 text-sm">No alerts by type</p>
          ) : (
            Object.entries(stats.by_type)
              .sort((a, b) => b[1] - a[1])
              .map(([type, count]) => (
                <TypeBar
                  key={type}
                  type={type}
                  count={count}
                  max={Math.max(...Object.values(stats.by_type))}
                />
              ))
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * StatBox Component - Display a single statistic
 */
interface StatBoxProps {
  label: string;
  value: string | number;
  color: 'blue' | 'red' | 'orange' | 'green';
  highlight?: boolean;
}

const StatBox: React.FC<StatBoxProps> = ({ label, value, color, highlight }) => {
  const colorClass = {
    blue: 'bg-blue-50 border-blue-200 text-blue-900',
    red: 'bg-red-50 border-red-200 text-red-900',
    orange: 'bg-orange-50 border-orange-200 text-orange-900',
    green: 'bg-green-50 border-green-200 text-green-900',
  }[color];

  return (
    <div
      className={`border ${colorClass} rounded-lg p-4 ${highlight ? 'border-2 shadow-lg' : ''}`}
    >
      <p className="text-sm font-medium opacity-75">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${highlight ? 'text-2xl' : ''}`}>{value}</p>
    </div>
  );
};

/**
 * SeverityBox Component
 */
interface SeverityBoxProps {
  icon: string;
  label: string;
  count: number;
  color: string;
}

const SeverityBox: React.FC<SeverityBoxProps> = ({ icon, label, count, color }) => {
  const bgClass = {
    red: 'bg-red-50',
    yellow: 'bg-yellow-50',
    blue: 'bg-blue-50',
  }[color];

  return (
    <div className={`${bgClass} border rounded-lg p-4 text-center`}>
      <div className="text-3xl mb-2">{icon}</div>
      <p className="text-sm font-medium text-gray-600">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{count}</p>
    </div>
  );
};

/**
 * PositionBox Component
 */
interface PositionBoxProps {
  position: string;
  count: number;
  hasCritical: boolean;
}

const PositionBox: React.FC<PositionBoxProps> = ({ position, count, hasCritical }) => (
  <div
    className={`border rounded-lg p-3 text-center ${
      hasCritical ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'
    }`}
  >
    <p className="text-sm font-semibold text-gray-900">{position}</p>
    <p className={`text-lg font-bold mt-1 ${hasCritical ? 'text-red-600' : 'text-gray-600'}`}>
      {count} {hasCritical ? '🔴' : ''}
    </p>
  </div>
);

/**
 * SourceBox Component
 */
interface SourceBoxProps {
  source: string;
  count: number;
  hasCritical: boolean;
}

const SourceBox: React.FC<SourceBoxProps> = ({ source, count, hasCritical }) => (
  <div
    className={`border rounded-lg p-3 text-center ${
      hasCritical ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'
    }`}
  >
    <p className="text-sm font-semibold text-gray-900">{source.toUpperCase()}</p>
    <p className={`text-lg font-bold mt-1 ${hasCritical ? 'text-red-600' : 'text-gray-600'}`}>
      {count} {hasCritical ? '🔴' : ''}
    </p>
  </div>
);

/**
 * TypeBar Component - Horizontal bar for alert types
 */
interface TypeBarProps {
  type: string;
  count: number;
  max: number;
}

const TypeBar: React.FC<TypeBarProps> = ({ type, count, max }) => {
  const percentage = (count / max) * 100;
  const typeLabel = type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm font-medium text-gray-700">{typeLabel}</span>
        <span className="text-sm font-bold text-gray-900">{count}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className="h-3 rounded-full bg-blue-500 transition-all"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
};

export default AlertSummary;
