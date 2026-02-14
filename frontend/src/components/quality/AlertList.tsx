/**
 * AlertList Component - Display and manage multiple quality alerts
 * 
 * Features:
 * - Severity-based filtering
 * - Position and source filtering
 * - Pagination support
 * - Real-time updates
 * - Bulk acknowledgment
 * - Loading and error states
 */

import React, { useState, useEffect } from 'react';
import AlertCard from './AlertCard';

interface Alert {
  id: string;
  alert_type: string;
  severity: 'critical' | 'warning' | 'info';
  message: string;
  position?: string;
  grade_source?: string;
  metric_value?: number;
  threshold_value?: number;
  quality_score?: number;
  generated_at: string;
  acknowledged: boolean;
  acknowledged_by?: string;
  acknowledged_at?: string;
}

interface AlertListProps {
  apiBaseUrl?: string;
  onAcknowledge?: (alertId: string, acknowledgedBy: string) => Promise<void>;
  autoRefreshInterval?: number; // in seconds
}

const AlertList: React.FC<AlertListProps> = ({
  apiBaseUrl = '/api',
  onAcknowledge,
  autoRefreshInterval = 60,
}) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [positionFilter, setPositionFilter] = useState<string>('all');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [acknowledgedFilter, setAcknowledgedFilter] = useState<string>('unacknowledged');

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalCount, setTotalCount] = useState(0);

  // Derived data
  const [positions, setPositions] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [stats, setStats] = useState({
    critical: 0,
    warning: 0,
    info: 0,
    total: 0,
  });

  // Fetch alerts
  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('days', '7');
      params.append('skip', String((page - 1) * pageSize));
      params.append('limit', String(pageSize));

      if (severityFilter !== 'all') {
        params.append('severity', severityFilter);
      }

      if (positionFilter !== 'all') {
        params.append('position', positionFilter);
      }

      if (sourceFilter !== 'all') {
        params.append('source', sourceFilter);
      }

      if (acknowledgedFilter !== 'all') {
        params.append('acknowledged', acknowledgedFilter === 'acknowledged' ? 'true' : 'false');
      }

      const response = await fetch(`${apiBaseUrl}/quality/alerts?${params}`);

      if (!response.ok) {
        throw new Error(`Failed to fetch alerts: ${response.statusText}`);
      }

      const data = await response.json();
      setAlerts(data.alerts || []);
      setTotalCount(data.total_count || 0);

      // Extract unique positions and sources
      const uniquePositions = new Set<string>();
      const uniqueSources = new Set<string>();
      data.alerts?.forEach((alert: Alert) => {
        if (alert.position) uniquePositions.add(alert.position);
        if (alert.grade_source) uniqueSources.add(alert.grade_source);
      });

      setPositions(Array.from(uniquePositions).sort());
      setSources(Array.from(uniqueSources).sort());

      // Update stats
      setStats({
        critical: data.critical_count || 0,
        warning: data.warning_count || 0,
        info: data.info_count || 0,
        total: data.total_count || 0,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
    } finally {
      setLoading(false);
    }
  };

  // Fetch alerts on component mount and when filters change
  useEffect(() => {
    fetchAlerts();
  }, [severityFilter, positionFilter, sourceFilter, acknowledgedFilter, page]);

  // Auto-refresh interval
  useEffect(() => {
    if (autoRefreshInterval <= 0) return;

    const interval = setInterval(() => {
      fetchAlerts();
    }, autoRefreshInterval * 1000);

    return () => clearInterval(interval);
  }, [autoRefreshInterval]);

  const handleAcknowledge = async (alertId: string, acknowledgedBy: string) => {
    if (onAcknowledge) {
      await onAcknowledge(alertId, acknowledgedBy);
    } else {
      const response = await fetch(`${apiBaseUrl}/quality/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ acknowledged_by: acknowledgedBy }),
      });

      if (!response.ok) {
        throw new Error('Failed to acknowledge alert');
      }
    }

    // Refresh the list
    await fetchAlerts();
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="space-y-6">
      {/* Statistics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Alerts"
          value={stats.total}
          icon="📊"
          color="bg-blue-50 border-blue-300"
        />
        <StatCard
          label="🔴 Critical"
          value={stats.critical}
          icon="🔴"
          color="bg-red-50 border-red-300"
        />
        <StatCard
          label="🟡 Warning"
          value={stats.warning}
          icon="🟡"
          color="bg-yellow-50 border-yellow-300"
        />
        <StatCard
          label="ℹ️ Info"
          value={stats.info}
          icon="ℹ️"
          color="bg-blue-50 border-blue-300"
        />
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-semibold mb-3 text-gray-700">Filters</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <FilterSelect
            label="Severity"
            value={severityFilter}
            onChange={setSeverityFilter}
            options={[
              { value: 'all', label: 'All Severities' },
              { value: 'critical', label: '🔴 Critical' },
              { value: 'warning', label: '🟡 Warning' },
              { value: 'info', label: 'ℹ️ Info' },
            ]}
          />

          <FilterSelect
            label="Position"
            value={positionFilter}
            onChange={setPositionFilter}
            options={[
              { value: 'all', label: 'All Positions' },
              ...positions.map(p => ({ value: p, label: p })),
            ]}
          />

          <FilterSelect
            label="Source"
            value={sourceFilter}
            onChange={setSourceFilter}
            options={[
              { value: 'all', label: 'All Sources' },
              ...sources.map(s => ({ value: s, label: s.toUpperCase() })),
            ]}
          />

          <FilterSelect
            label="Status"
            value={acknowledgedFilter}
            onChange={setAcknowledgedFilter}
            options={[
              { value: 'all', label: 'All' },
              { value: 'unacknowledged', label: 'Unacknowledged' },
              { value: 'acknowledged', label: 'Acknowledged' },
            ]}
          />
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-8">
          <div className="text-center">
            <div className="animate-spin text-4xl mb-2">⏳</div>
            <p className="text-gray-600">Loading alerts...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-300 text-red-800 p-4 rounded">
          <h3 className="font-semibold mb-1">Error Loading Alerts</h3>
          <p className="text-sm">{error}</p>
          <button
            onClick={fetchAlerts}
            className="mt-3 px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 text-sm font-medium"
          >
            Retry
          </button>
        </div>
      )}

      {/* Alerts List */}
      {!loading && !error && (
        <>
          {alerts.length === 0 ? (
            <div className="text-center py-8 text-gray-600">
              <p className="text-lg">✨ No alerts found</p>
              <p className="text-sm">Great job! All systems are healthy.</p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                {alerts.map(alert => (
                  <AlertCard
                    key={alert.id}
                    alert={alert}
                    onAcknowledge={handleAcknowledge}
                    onRefresh={fetchAlerts}
                  />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex justify-between items-center p-4 bg-white border border-gray-200 rounded-lg">
                  <span className="text-sm text-gray-600">
                    Page {page} of {totalPages} ({totalCount} total alerts)
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(Math.max(1, page - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setPage(Math.min(totalPages, page + 1))}
                      disabled={page === totalPages}
                      className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

/**
 * StatCard Component - Display a single statistic
 */
interface StatCardProps {
  label: string;
  value: number;
  icon: string;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, icon, color }) => (
  <div className={`border-l-4 ${color} p-4 rounded`}>
    <div className="text-2xl mb-1">{icon}</div>
    <p className="text-gray-600 text-sm">{label}</p>
    <p className="text-2xl font-bold text-gray-900">{value}</p>
  </div>
);

/**
 * FilterSelect Component - Reusable filter dropdown
 */
interface FilterSelectProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}

const FilterSelect: React.FC<FilterSelectProps> = ({ label, value, onChange, options }) => (
  <div>
    <label className="block text-xs font-semibold text-gray-700 mb-1">{label}</label>
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      {options.map(option => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  </div>
);

export default AlertList;
