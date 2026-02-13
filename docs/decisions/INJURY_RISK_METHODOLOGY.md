# Injury Risk Assessment - V1 Specification
**Date:** February 13, 2026  
**For Sprint 5:** US-051  
**Status:** Draft - Awaiting PO Review

---

## Overview

Injury Risk Assessment is an endpoint providing injury history, patterns, and risk percentile for a prospect. This v1 implementation aggregates historical injury data and compares to position-group norms.

---

## Data Model

### Prospect Injury Table
```sql
CREATE TABLE prospect_injuries (
    id SERIAL PRIMARY KEY,
    prospect_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    injury_type VARCHAR(255),      -- "ACL", "MCL", "Hamstring", etc.
    body_part VARCHAR(255),        -- "Knee", "Shoulder", "Leg", etc.
    severity VARCHAR(50),          -- "Minor", "Moderate", "Severe"
    games_missed INTEGER,          -- Games missed due to injury
    status VARCHAR(50),            -- "Active", "Recovered", "Aggravated", "Reinjured"
    source VARCHAR(255),           -- "NFL.com", "ESPN", "News", etc.
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (prospect_id) REFERENCES prospects(id)
);

CREATE TABLE injury_patterns (
    id SERIAL PRIMARY KEY,
    position VARCHAR(50),
    injury_type VARCHAR(255),
    frequency_percent FLOAT,       -- % of players with this injury type
    avg_games_missed INTEGER,
    career_impact VARCHAR(50),     -- "Minimal", "Moderate", "Severe"
    return_rate_percent FLOAT,     -- % who return to play effectively
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Risk Percentile Calculation

**Percentile:** Where a prospect's injury history falls relative to their position group.

### Methodology:

```python
def calculate_injury_risk_percentile(prospect, position):
    """
    Calculate injury risk percentile for a prospect.
    
    Factors:
    - Total number of injuries
    - Injury severity (weighted)
    - Recurrence patterns
    - Days missed from play
    """
    
    # Score prospect's injury history (0-100, 0=safest, 100=most injuries)
    prospect_score = calculate_injury_burden_score(prospect)
    
    # Get all prospects in position group with injury data
    position_cohort = get_position_cohort(position, prospect.draft_year)
    cohort_scores = [calculate_injury_burden_score(p) for p in position_cohort]
    
    # Calculate percentile rank
    percentile = percentileofscore(cohort_scores, prospect_score)
    
    return percentile  # 0-100, where 100 = most injured
```

### Injury Burden Score Formula:

```python
def calculate_injury_burden_score(prospect):
    """
    Calculate numeric injury burden (0-100).
    
    Formula:
    - Base score: number of injuries
    - Severity multiplier: (Severe=3, Moderate=2, Minor=1)
    - Recurrence penalty: +20 per recurrence
    - Days missed factor: (days_missed / 365) * 10
    """
    
    injuries = prospect.injuries
    
    if not injuries:
        return 0
    
    base_score = len(injuries) * 10  # 10 points per injury
    
    severity_score = sum(
        SEVERITY_WEIGHTS[injury.severity]  # 1, 2, or 3
        for injury in injuries
    ) * 10
    
    recurrence_score = count_recurrences(injuries) * 20
    
    # Days missed (normalize to 0-100 scale)
    total_days_missed = sum(injury.games_missed * 7 for injury in injuries)
    days_score = min(100, (total_days_missed / 365) * 20)
    
    # Weighted combination
    total_score = (
        base_score * 0.25 +
        severity_score * 0.35 +
        recurrence_score * 0.20 +
        days_score * 0.20
    )
    
    return min(100, total_score)

SEVERITY_WEIGHTS = {
    "Minor": 1,      # Precautionary, brief absence
    "Moderate": 2,   # Miss 2-4 weeks
    "Severe": 3,     # Miss > 4 weeks or season-ending
}
```

### Recurrence Definition:

**Recurrence:** Same injury type within 12 months

```python
def count_recurrences(injuries):
    """
    Count recurrences: same injury type within 12 months.
    """
    sorted_injuries = sorted(injuries, key=lambda x: x.year)
    recurrence_count = 0
    
    for i, current_injury in enumerate(sorted_injuries):
        for j in range(i):
            prior_injury = sorted_injuries[j]
            if (
                current_injury.injury_type == prior_injury.injury_type and
                (current_injury.year - prior_injury.year) <= 1
            ):
                recurrence_count += 1
                break  # Count only once per injury type per year
    
    return recurrence_count
```

### Example Percentile Calculation:

**Prospect: Generic WR**
- Total injuries: 2 (ACL in 2022, hamstring in 2023)
- Severity: Severe (ACL), Moderate (hamstring)
- Recurrences: 0
- Days missed: 120 days
- Burden score: 38

**Position cohort (WR):** 
- 200 prospects with injury data
- Scores: 10-85, median ~30

**Percentile:** 65th percentile (more injuries than ~65% of WRs) ⚠️ Higher risk

---

## Risk Severity Classification

```python
def classify_risk_level(percentile, injury_count, severity_codes):
    """
    Classify overall risk level based on percentile and details.
    """
    
    # Base classification on percentile
    if percentile >= 75:
        base_level = "HIGH"
    elif percentile >= 50:
        base_level = "MODERATE"
    else:
        base_level = "LOW"
    
    # Adjust for recurrences (very negative signal)
    recurrences = count_recurrences(injuries)
    if recurrences >= 2:
        base_level = "HIGH"  # Upgrade to high if repeat injuries
    
    # Adjust for major injuries (ACL, Achilles)
    major_injuries = [i for i in injuries if i.injury_type in ["ACL", "Achilles"]]
    if len(major_injuries) >= 2:
        base_level = "HIGH"  # Upgrade if multiple major injuries
    
    return base_level

RISK_LEVELS = {
    "LOW": "< 25th percentile | Minimal injury history",
    "MODERATE": "25-75th percentile | Typical for position",
    "HIGH": "> 75th percentile | Significant injury concerns",
}
```

---

## Endpoint Response

### Request:
```
GET /api/analytics/injury-risk/:prospect_id
```

### Response:
```json
{
  "prospect_id": 12345,
  "prospect_name": "Generic WR",
  "position": "WR",
  
  "injury_history": [
    {
      "year": 2023,
      "injury_type": "Hamstring",
      "body_part": "Leg",
      "severity": "Moderate",
      "games_missed": 4,
      "status": "Recovered",
      "details": "Pulled hamstring in preseason, missed 4 games"
    },
    {
      "year": 2022,
      "injury_type": "ACL",
      "body_part": "Knee",
      "severity": "Severe",
      "games_missed": 16,
      "status": "Recovered",
      "details": "ACL tear in week 2, redshirt season"
    }
  ],
  
  "summary": {
    "total_injuries": 2,
    "games_missed": 20,
    "major_injuries": 1,
    "recurrence_risk": "LOW"
  },
  
  "risk_assessment": {
    "percentile": 65,
    "percentile_description": "65th percentile for WR (more injured than 65% of WRs)",
    "risk_level": "MODERATE",
    "risk_level_description": "Injury history above average for position",
    "recurrence_risk": "low",
    "recurrence_risk_description": "Different body parts injured, low risk of repeat injury"
  },
  
  "position_patterns": {
    "position": "WR",
    "common_injuries": [
      {"injury": "ACL", "frequency_percent": 8.5, "avg_games_missed": 16},
      {"injury": "Hamstring", "frequency_percent": 12.3, "avg_games_missed": 4},
      {"injury": "Ankle Sprain", "frequency_percent": 15.2, "avg_games_missed": 2}
    ],
    "injury_return_rate": 92,
    "injury_return_rate_description": "92% of WRs return to effective play after injury"
  },
  
  "comparable_prospects": [
    {
      "prospect_id": 67890,
      "name": "Similar Player 1",
      "injuries": "ACL x1, Hamstring x1",
      "risk_percentile": 68,
      "draft_round": "2nd Round"
    },
    {
      "prospect_id": 67891,
      "name": "Similar Player 2",
      "injuries": "ACL x1, Hamstring x1",
      "risk_percentile": 62,
      "draft_round": "3rd Round"
    }
  ]
}
```

---

## Related Prospects Calculation

**Goal:** Show prospects with similar injury profiles to help analysts understand patterns.

### Algorithm:

```python
def find_similar_injury_profiles(prospect, position, limit=5):
    """
    Find prospects with similar injury patterns.
    """
    
    target_profile = {
        "injury_types": get_injury_types(prospect),  # ["ACL", "Hamstring"]
        "total_injuries": len(prospect.injuries),
        "games_missed": sum(i.games_missed for i in prospect.injuries),
    }
    
    position_cohort = get_position_cohort(position)
    similarities = []
    
    for candidate in position_cohort:
        if candidate.id == prospect.id:
            continue
        
        candidate_profile = {
            "injury_types": get_injury_types(candidate),
            "total_injuries": len(candidate.injuries),
            "games_missed": sum(i.games_missed for i in candidate.injuries),
        }
        
        # Similarity score
        type_match = len(set(target_profile["injury_types"]) & 
                        set(candidate_profile["injury_types"])) / max(
                            len(set(target_profile["injury_types"]) | 
                                set(candidate_profile["injury_types"])), 1
                        )  # Jaccard similarity
        
        injury_count_match = 1 - abs(
            target_profile["total_injuries"] - candidate_profile["total_injuries"]
        ) / max(target_profile["total_injuries"], 1)
        
        games_match = 1 - abs(
            target_profile["games_missed"] - candidate_profile["games_missed"]
        ) / max(target_profile["games_missed"], 1)
        
        # Weighted average
        similarity_score = (
            type_match * 0.50 +
            injury_count_match * 0.30 +
            games_match * 0.20
        )
        
        similarities.append({
            "prospect": candidate,
            "similarity": similarity_score
        })
    
    # Return top N most similar
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    return similarities[:limit]
```

---

## Data Availability & Assumptions

### What We Have:
- ✅ Basic injury data from NFL.com (where collected)
- ✅ College injury history (if captured during web scraping)

### What We May Not Have:
- ⚠️ Complete historical injury database for all positions
- ⚠️ Pre-draft medical evaluation data
- ⚠️ Detailed injury notes (will have basic info only)

### Approach for Sprint 5:
1. Use available data (football-reference.com, pro-football-reference.com)
2. Document data gaps clearly in response
3. Flag prospects with incomplete data
4. Plan for enhanced injury database in future sprints

### Confidence Scoring for Injury Data:
```python
def calculate_data_confidence(prospect):
    """
    Confidence in injury assessment based on data completeness.
    """
    confidence = 80  # Base
    
    if not prospect.has_injury_data:
        confidence = 20  # Low confidence if no data
    elif len(prospect.injuries) == 0:
        confidence = 95  # High confidence in "no injuries"
    else:
        # Reduce if missing details
        for injury in prospect.injuries:
            if not injury.severity:
                confidence -= 5
            if not injury.games_missed:
                confidence -= 5
    
    return confidence
```

---

## Implementation Checklist

- [ ] Database: Create `prospect_injuries` and `injury_patterns` tables
- [ ] Data Collection: Populate injury data from available sources
- [ ] Percentile Calculation: Implement injury burden scoring algorithm
- [ ] Recurrence Detection: Identify same-injury patterns
- [ ] Risk Classification: Assign risk levels
- [ ] Similar Prospects: Implement matching algorithm
- [ ] Caching: Cache injury data and percentiles
- [ ] Endpoint: `GET /api/analytics/injury-risk/:prospect_id`
- [ ] Response: Full JSON with all fields
- [ ] Documentation: User guide explaining risk metrics
- [ ] Validation: Compare to medical evaluation data where available

---

## Future Enhancements (Post-Launch)

- [ ] Integrate pre-draft medical evaluation data
- [ ] Injury prediction models (which prospects likely to get injured)
- [ ] Team-specific injury adjustment (team medical history)
- [ ] Positional injury tracking (e.g., ACL risk by position over time)
- [ ] Recovery timeline prediction

---

**Next Steps:** PO to confirm methodology. Data availability assessment needed before implementation.

