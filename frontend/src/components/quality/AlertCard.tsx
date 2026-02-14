/**
 * AlertCard Component - Display individual quality alerts
 * 
 * Features:
 * - Severity-based color coding (🔴 critical, 🟡 warning, ℹ️ info)
 * - Alert metadata display (position, source, timestamp)
 * - Quick acknowledge button
 * - Responsive design with TailwindCSS
 */

import React, { useState } from 'react';

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

interface AlertCardProps {
  alert: Alert;
  onAcknowledge: (alertId: string, acknowledgedBy: string) => Promise<void>;
  onRefresh?: () => void;
}

const AlertCard: React.FC<AlertCardProps> = ({ alert, onAcknowledge, onRefresh }) => {
  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const severityConfig = {
    critical: {
      icon: '🔴',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-300',
      textColor: 'text-red-900',
      badgeColor: 'bg-red-200 text-red-800',
    },
    warning: {
      icon: '🟡',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-300',
      textColor: 'text-yellow-900',
      badgeColor: 'bg-yellow-200 text-yellow-800',
    },
    info: {
      icon: 'ℹ️',
      bgColor: 'bg-blue-50',
      borderColor: 'border-blue-300',
      textColor: 'text-blue-900',
      badgeColor: 'bg-blue-200 text-blue-800',
    },
  };

  const config = severityConfig[alert.severity];

  const handleAcknowledge = async () => {
    setIsAcknowledging(true);
    setError(null);
    try {
      await onAcknowledge(alert.id, 'dashboard-user');
      if (onRefresh) onRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge alert');
    } finally {
      setIsAcknowledging(false);
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const alertTypeLabel = alert.alert_type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <div
      className={`${config.bgColor} border-l-4 ${config.borderColor} p-4 mb-3 rounded shadow-sm hover:shadow-md transition-shadow`}
    >
      {/* Header with severity and type */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{config.icon}</span>
          <div>
            <h3 className={`font-semibold ${config.textColor}`}>
              {alertTypeLabel}
            </h3>
            <p className="text-sm text-gray-600">{alert.message}</p>
          </div>
        </div>
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${config.badgeColor}`}
        >
          {alert.severity.toUpperCase()}
        </span>
      </div>

      {/* Alert details grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3 text-sm">
        {alert.position && (
          <div>
            <span className="text-gray-600">Position:</span>
            <p className="font-medium">{alert.position}</p>
          </div>
        )}
        {alert.grade_source && (
          <div>
            <span className="text-gray-600">Source:</span>
            <p className="font-medium">{alert.grade_source.toUpperCase()}</p>
          </div>
        )}
        {alert.metric_value !== undefined && (
          <div>
            <span className="text-gray-600">Current:</span>
            <p className="font-medium">{alert.metric_value.toFixed(1)}</p>
          </div>
        )}
        {alert.threshold_value !== undefined && (
          <div>
            <span className="text-gray-600">Threshold:</span>
            <p className="font-medium">{alert.threshold_value.toFixed(1)}</p>
          </div>
        )}
      </div>

      {/* Quality score if available */}
      {alert.quality_score !== undefined && (
        <div className="mb-3 p-2 bg-white rounded text-sm">
          <span className="text-gray-600">Quality Score: </span>
          <span className="font-semibold">{alert.quality_score.toFixed(1)}/100</span>
          <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
            <div
              className={`h-2 rounded-full transition-all ${
                alert.quality_score >= 75 ? 'bg-green-500' : 'bg-orange-500'
              }`}
              style={{ width: `${Math.min(alert.quality_score, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Timestamp and acknowledgment info */}
      <div className="flex items-center justify-between text-xs text-gray-600 mb-3">
        <span>Generated: {formatTime(alert.generated_at)}</span>
        {alert.acknowledged && (
          <span className="text-green-600 font-medium">
            ✓ Acknowledged by {alert.acknowledged_by} at {formatTime(alert.acknowledged_at || '')}
          </span>
        )}
      </div>

      {/* Error message if present */}
      {error && (
        <div className="mb-3 p-2 bg-red-100 border border-red-300 text-red-700 text-sm rounded">
          {error}
        </div>
      )}

      {/* Action button */}
      {!alert.acknowledged && (
        <button
          onClick={handleAcknowledge}
          disabled={isAcknowledging}
          className={`w-full py-2 px-3 rounded font-medium text-sm transition-colors ${
            isAcknowledging
              ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
              : 'bg-green-500 text-white hover:bg-green-600 active:bg-green-700'
          }`}
        >
          {isAcknowledging ? 'Acknowledging...' : 'Acknowledge Alert'}
        </button>
      )}
    </div>
  );
};

export default AlertCard;
