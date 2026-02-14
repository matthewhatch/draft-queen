# Quality Dashboard Components

**Location**: `frontend/src/components/quality/`  
**Status**: Complete (4 components, 1 page)  
**Framework**: React + TypeScript  
**Styling**: TailwindCSS  

---

## Components Overview

### 1. AlertCard Component

**File**: `AlertCard.tsx`  
**Purpose**: Display individual quality alert with full details  

**Features**:
- Severity-based color coding (🔴 critical, 🟡 warning, ℹ️ info)
- Alert metadata display (position, source, metrics)
- Quality score progress bar
- Quick acknowledge button
- Responsive card layout
- Loading and error states

**Props**:
```typescript
interface AlertCardProps {
  alert: Alert;
  onAcknowledge: (alertId: string, acknowledgedBy: string) => Promise<void>;
  onRefresh?: () => void;
}
```

**Usage**:
```tsx
import { AlertCard } from '@/components/quality';

<AlertCard 
  alert={alertData}
  onAcknowledge={handleAcknowledge}
  onRefresh={handleRefresh}
/>
```

**Key Methods**:
- `handleAcknowledge()` - Acknowledge single alert
- `formatTime()` - Format timestamps

---

### 2. AlertList Component

**File**: `AlertList.tsx`  
**Purpose**: Display and manage multiple alerts with filtering and pagination  

**Features**:
- Multi-dimensional filtering (severity, position, source, acknowledgment status)
- Pagination support with configurable page size
- Statistics cards (total, critical, warning, info)
- Real-time auto-refresh capability
- Dynamic filter dropdowns based on data
- Responsive grid layout
- Loading and error states with retry

**Props**:
```typescript
interface AlertListProps {
  apiBaseUrl?: string;
  onAcknowledge?: (alertId: string, acknowledgedBy: string) => Promise<void>;
  autoRefreshInterval?: number; // seconds, 0 = disabled
}
```

**Usage**:
```tsx
import { AlertList } from '@/components/quality';

<AlertList 
  apiBaseUrl="/api"
  autoRefreshInterval={60}
/>
```

**Sub-components**:
- `StatCard` - Display single statistic
- `FilterSelect` - Reusable filter dropdown

**API Endpoints Used**:
- `GET /api/quality/alerts` - Retrieve alerts with filters
- `POST /api/quality/alerts/{id}/acknowledge` - Acknowledge alert

---

### 3. AlertSummary Component

**File**: `AlertSummary.tsx`  
**Purpose**: Display alert statistics and trends  

**Features**:
- Overall statistics (total, unacknowledged, critical, oldest alert age)
- Unacknowledged alerts breakdown by severity
- Alerts by position with critical highlighting
- Alerts by source with critical highlighting
- Alerts by type with horizontal bar charts
- Critical positions and sources highlighting
- Real-time auto-refresh capability
- Responsive grid layout

**Props**:
```typescript
interface AlertSummaryProps {
  apiBaseUrl?: string;
  days?: number;
  autoRefreshInterval?: number; // seconds
}
```

**Usage**:
```tsx
import { AlertSummary } from '@/components/quality';

<AlertSummary 
  apiBaseUrl="/api"
  days={7}
  autoRefreshInterval={60}
/>
```

**Sub-components**:
- `StatBox` - Display statistic in colored box
- `SeverityBox` - Show severity breakdown
- `PositionBox` - Show position with critical indicator
- `SourceBox` - Show source with critical indicator
- `TypeBar` - Horizontal bar chart for alert types

**API Endpoints Used**:
- `GET /api/quality/alerts/summary` - Retrieve alert statistics

---

### 4. QualityDashboard Page

**File**: `pages/QualityDashboard.tsx`  
**Purpose**: Main dashboard page combining all quality components  

**Features**:
- Tabbed interface (Alerts, Summary)
- Manual refresh button
- Responsive layout
- Header with description
- Footer with timestamp and refresh interval info
- Responsive design for mobile/tablet/desktop

**Layout**:
```
┌─ Header (Title + Refresh Button)
├─ Tabs (Alerts | Summary)
├─ Main Content
│  ├─ Alerts Tab
│  │  └─ AlertList Component
│  └─ Summary Tab
│     └─ AlertSummary Component
└─ Footer
```

**Usage**:
```tsx
import QualityDashboard from '@/pages/QualityDashboard';

// In your router configuration
<Route path="/quality" element={<QualityDashboard />} />
```

---

## Type Definitions

### Alert Interface
```typescript
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
```

### AlertStats Interface
```typescript
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
```

---

## Styling Guide

### Color Scheme
```
Critical:  🔴 Red     (bg-red-50, border-red-300, text-red-900)
Warning:   🟡 Yellow  (bg-yellow-50, border-yellow-300, text-yellow-900)
Info:      ℹ️ Blue    (bg-blue-50, border-blue-300, text-blue-900)
```

### Responsive Breakpoints
- Mobile: Single column layout
- Tablet: 2-column grid (md:)
- Desktop: 3-4 column grid

### TailwindCSS Classes Used
- Grid: `grid`, `grid-cols-1`, `md:grid-cols-2`, `md:grid-cols-4`
- Colors: `bg-red-50`, `border-red-300`, `text-red-900`
- Spacing: `p-4`, `mb-3`, `gap-3`, `space-y-6`
- Typography: `text-sm`, `font-semibold`, `text-gray-900`
- States: `hover:`, `disabled:`, `active:`

---

## API Integration

### Required Endpoints

1. **GET /api/quality/alerts**
   - Query params: `days`, `severity`, `position`, `source`, `acknowledged`, `skip`, `limit`
   - Returns: `AlertListResponse`

2. **POST /api/quality/alerts/{alert_id}/acknowledge**
   - Body: `{ acknowledged_by: string }`
   - Returns: Updated `AlertResponse`

3. **GET /api/quality/alerts/summary**
   - Query params: `days`, `severity`
   - Returns: `AlertStats`

### Configuration
```typescript
// Environment variables
REACT_APP_API_URL=http://localhost:8000/api
```

---

## Features in Detail

### Filtering System
- **Severity**: Critical, Warning, Info
- **Position**: QB, RB, WR, TE, OL, DL, LB, DB (dynamic)
- **Source**: PFF, ESPN, etc. (dynamic)
- **Status**: All, Acknowledged, Unacknowledged

### Pagination
- Default page size: 10 alerts
- Configurable page size
- Previous/Next navigation
- Total count display

### Auto-Refresh
- Configurable interval (default 60 seconds)
- Can be disabled (interval = 0)
- Maintains current filters during refresh
- Shows loading state

### Acknowledgment
- Single alert acknowledgment via button
- Bulk acknowledgment ready (future feature)
- Tracks user/system and timestamp
- Auto-refresh after acknowledgment

---

## Performance Considerations

### Optimization Techniques
- Component lazy loading ready
- Pagination to limit DOM elements
- Efficient re-renders with proper dependencies
- Debounced API calls (future enhancement)
- Cached data structures

### Best Practices
- Use React.memo for sub-components
- Proper cleanup of intervals
- Error boundaries recommended
- Loading states to prevent UI flash

---

## Testing

### Unit Tests (Recommended)
- AlertCard component rendering
- Alert acknowledgment flow
- Filter application
- Pagination logic
- Error handling

### Integration Tests
- Full alert retrieval and display
- Filtering + pagination combination
- API error scenarios
- Auto-refresh behavior

### Example Test
```tsx
describe('AlertList', () => {
  test('should display alerts from API', async () => {
    const { getByText } = render(<AlertList />);
    await waitFor(() => {
      expect(getByText(/Alert Message/)).toBeInTheDocument();
    });
  });
});
```

---

## Future Enhancements

### Phase 6 (Planned)
- [ ] Bulk acknowledgment UI
- [ ] Alert history/timeline view
- [ ] Custom date range picker
- [ ] Export to CSV/PDF
- [ ] Email digest preview modal
- [ ] Real-time updates via WebSocket
- [ ] Chart visualizations (Chart.js, D3)
- [ ] Mobile app version
- [ ] Dark mode support
- [ ] Accessibility improvements (WCAG 2.1)

### Customization Points
- Theme configuration
- API endpoint customization
- Refresh interval tuning
- Page size adjustment
- Icon/emoji replacements

---

## Summary

The Quality Dashboard provides a comprehensive, production-ready interface for monitoring data quality alerts. With filtering, pagination, real-time updates, and responsive design, it meets all Phase 5 requirements for dashboard integration.

**Key Statistics**:
- 4 React components (750+ LOC TypeScript)
- 1 main dashboard page
- Full TypeScript type safety
- TailwindCSS styling (responsive)
- 3 API endpoints integrated
- Auto-refresh capability
- Error handling throughout

**Status**: ✅ Complete and ready for integration
