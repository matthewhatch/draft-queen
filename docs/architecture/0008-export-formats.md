# ADR 0008: Data Export Formats - JSON, CSV, Parquet

**Date:** 2026-02-09  
**Status:** Accepted

## Context

Analysts need to export prospect data for downstream analysis in:
- Spreadsheets (Excel workflows)
- Python/R scripts (statistical analysis)
- Data warehouses (bulk analysis)
- Sharing with external consultants

Formats have different trade-offs: human-readability, file size, tool compatibility, schema preservation.

## Decision

We support **three export formats**:

1. **CSV** (for Excel and basic analysis)
   - Use case: Spreadsheet analysis, sharing with non-technical stakeholders
   - Pros: Universal compatibility, human-readable, smallest for small datasets
   - Cons: Loses schema info, type ambiguity, poor for nested data

2. **JSON** (for web services and Python)
   - Use case: Python/JavaScript processing, API integration, nested data
   - Pros: Preserves types, schema-aware, widely supported
   - Cons: Verbose, larger file sizes, slower parsing than binary

3. **Parquet** (for big data tools)
   - Use case: DuckDB, Pandas, Polars, cloud data warehouses
   - Pros: Columnar compression, schema preservation, fast
   - Cons: Less human-readable, requires special tools

**Export API**

```
GET /api/prospects/export?format=csv
GET /api/prospects/export?format=json
GET /api/prospects/export?format=parquet

GET /api/prospects/export?format=csv&fields=name,position,college,forty_time
GET /api/prospects/export?format=json&filter={position:QB}
```

**Implementation**

```python
from fastapi.responses import StreamingResponse
import pandas as pd
import pyarrow.parquet as pq

@app.get("/api/prospects/export")
async def export_prospects(
    format: str = "csv",
    fields: Optional[str] = None,
    filter_json: Optional[str] = None
):
    """Export prospects in requested format"""
    
    # Query database
    prospects = get_prospects_query(filter_json)
    df = pd.DataFrame(prospects)
    
    # Filter fields if specified
    if fields:
        field_list = fields.split(',')
        df = df[field_list]
    
    # Format export
    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=prospects.csv"}
        )
    
    elif format == "json":
        json_bytes = df.to_json(orient='records').encode()
        return StreamingResponse(
            iter([json_bytes]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=prospects.json"}
        )
    
    elif format == "parquet":
        output = io.BytesIO()
        table = pa.Table.from_pandas(df)
        pq.write_table(table, output)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename=prospects.parquet"}
        )
```

**Example Jupyter Usage**

```python
import pandas as pd
import requests

# Export and load directly into Jupyter
response = requests.get(
    "http://api.example.com/api/prospects/export?format=parquet",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

df = pd.read_parquet(io.BytesIO(response.content))
print(df.describe())
print(df.groupby('position').agg({
    'forty_time': 'mean',
    'height': 'mean',
    'weight': 'mean'
}))
```

**Performance Considerations**

| Format | Size | Speed | Schema |
|--------|------|-------|--------|
| CSV | Large (2,000 prospects: 5 MB) | Medium | Lost |
| JSON | Large (2,000 prospects: 8 MB) | Medium | Preserved |
| Parquet | Small (2,000 prospects: 1 MB) | Fast | Preserved |

**Schema Definitions**

```json
// prospects.schema.json
{
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "name", "type": "string"},
    {"name": "position", "type": "string"},
    {"name": "college", "type": "string"},
    {"name": "height", "type": "integer", "unit": "inches"},
    {"name": "weight", "type": "integer", "unit": "pounds"},
    {"name": "forty_time", "type": "number", "unit": "seconds"},
    {"name": "bench_press", "type": "integer", "unit": "reps"},
    {"name": "vertical", "type": "number", "unit": "inches"},
    {"name": "broad_jump", "type": "integer", "unit": "inches"}
  ]
}
```

## Consequences

### Positive
- Flexibility: analysts choose format for their workflow
- Compatibility: all major tools supported
- Performance: Parquet enables large-scale analysis
- Schema preservation: JSON and Parquet preserve data types
- Accessibility: CSV available for non-technical users

### Negative
- Support burden: three formats to test and maintain
- Complexity: export logic more complex
- CSV limitations: type ambiguity; common source of bugs
- Parquet learning curve: analysts less familiar with columnar format

### CSV Type Ambiguity Mitigation
- Include schema in JSON export: {"schema": {...}, "data": [...]}
- Document type conversions: how to read CSV correctly
- Recommend: use JSON or Parquet for programmatic analysis

## Alternatives Considered

### JSON-LD (Semantic Web Format)
- Better: machine-readable schema
- Worse: verbose; specialized tooling needed
- Decision: Rejected; standard JSON sufficient

### Arrow IPC (Binary Wire Format)
- Better: efficient binary format
- Worse: less tool support than Parquet
- Decision: Rejected; Parquet more widely supported

### Excel (.xlsx)
- Better: familiar to business users
- Worse: size, complexity, limited formula preservation
- Decision: Rejected; CSV adequate for Excel users

### XML
- Rejected: verbose, outdated

### Protocol Buffers
- Better: efficient, schema-driven
- Worse: requires protobuf tooling
- Decision: Rejected for external sharing

## Related Decisions
- ADR-0003: API Design (export endpoints)
- ADR-0004: Caching Strategy (export endpoints bypass cache, direct DB)
