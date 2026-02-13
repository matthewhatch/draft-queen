# Production Readiness Scoring - V1 Specification
**Date:** February 13, 2026  
**For Sprint 5:** US-052  
**Status:** Draft - Awaiting PO Review

---

## Overview

Production readiness is a 0-100 score indicating how ready a prospect is for immediate NFL impact. This v1 implementation uses historical measurables and college production data to predict readiness.

---

## Scoring Formula

```
Production Readiness Score = 
    (Measurables Score × 0.40) +
    (College Production Score × 0.40) +
    (Age/Experience Score × 0.20) +
    Position-Specific Adjustment
```

**Final score:** Min(100, calculated score)

---

## Component 1: Measurables Score (40% weight)

Normalized score from 0-100 based on physical attributes relative to position group.

### Factors (equal weight within component):
- Height (optimal range per position)
- Weight (optimal range per position)
- 40-time (faster is better, but position-dependent)
- Vertical Jump (higher is better)
- Broad Jump (longer is better)
- Bench Press Reps (more is better, if available)

### Calculation:
```python
def calculate_measurables_score(prospect, position):
    """
    Calculate measurables score as percentile within position group.
    """
    factors = {
        'height': get_position_percentile(prospect.height, position, 'height'),
        'weight': get_position_percentile(prospect.weight, position, 'weight'),
        '40_time': get_position_percentile_inverse(prospect.forty_time, position, '40'),
        'vertical': get_position_percentile(prospect.vertical, position, 'vertical'),
        'broad_jump': get_position_percentile(prospect.broad_jump, position, 'broad'),
    }
    
    # Average across factors (exclude if missing)
    available_factors = [v for v in factors.values() if v is not None]
    score = sum(available_factors) / len(available_factors) if available_factors else 50
    
    return score  # 0-100
```

### Position-Specific Ranges (Examples):

**Quarterback:**
- Height: 6'0" - 6'4" (optimal), 5'11" - 6'5" (acceptable)
- Weight: 200-230 lbs

**Running Back:**
- Height: 5'8" - 5'11"
- Weight: 200-230 lbs
- 40-time: < 4.7s

**Wide Receiver:**
- Height: 5'10" - 6'3"
- Weight: 185-215 lbs
- 40-time: < 4.6s

**Edge Rusher:**
- Height: 6'2" - 6'5"
- Weight: 240-280 lbs
- 40-time: < 4.8s

**Cornerback:**
- Height: 5'10" - 6'1"
- Weight: 185-205 lbs
- 40-time: < 4.5s

---

## Component 2: College Production Score (40% weight)

Normalized score from 0-100 based on college performance metrics relative to position.

### Position-Specific Metrics:

**Quarterback:**
- Pass attempts per game
- Completion percentage
- TD:INT ratio
- College level (P5 vs. G5)
- Scoring: (Comp% × 0.3) + (TD:INT × 0.3) + (Attempts × 0.2) + (P5 bonus × 0.2)

**Running Back:**
- Yards per game
- Yards per carry
- TD:Carry ratio
- Receiving role (if applicable)
- Scoring: (Yards/Game × 0.4) + (Yards/Carry × 0.3) + (TD Ratio × 0.3)

**Wide Receiver:**
- Catch percentage
- Yards per game
- TD percentage
- Consistency (game-to-game std dev)
- Scoring: (Catch% × 0.4) + (Yards/Game × 0.3) + (TD% × 0.2) + (Consistency × 0.1)

**Edge Rusher:**
- Sacks per game
- Pressures per game
- Tackles for loss
- Consistency
- Scoring: (Sacks/Game × 0.4) + (Pressures/Game × 0.3) + (TFL × 0.3)

**Cornerback:**
- Interceptions per season
- Pass breakups per game
- Catch rate allowed
- Tackles for loss
- Scoring: (INT/Season × 0.3) + (Breakups × 0.3) + (Tackles × 0.2) + (Yards Allowed × 0.2 inverse)

**Interior Defensive Line:**
- Tackles per game
- Sacks per game
- Pressures per game
- Scoring: (Tackles × 0.4) + (Sacks × 0.3) + (Pressures × 0.3)

**Linebacker:**
- Tackles per game
- Sacks and pressures
- Passes defended
- Run support consistency
- Scoring: (Tackles × 0.4) + (Sacks × 0.2) + (Coverage × 0.2) + (Consistency × 0.2)

### Calculation:
```python
def calculate_production_score(prospect, position):
    """
    Calculate college production score as percentile within position group.
    """
    metrics = get_position_metrics(position, prospect)
    scores = {}
    
    for metric_name, metric_value in metrics.items():
        percentile = get_position_percentile(
            metric_value,
            position,
            metric_name
        )
        scores[metric_name] = percentile
    
    # Apply position-specific weights
    weights = get_position_weights(position)
    score = sum(scores[metric] * weights[metric] for metric in scores)
    
    return score  # 0-100
```

---

## Component 3: Age & Experience Score (20% weight)

Score based on age and college career length.

### Optimal Profiles by Position:

**QB, WR, TE, Edge, DB:**
- Optimal: 2-3 years college experience, age 20-22 at draft
- Score bonus for 3+ years vs penalty for < 2 years

**RB, DL, LB:**
- Optimal: 3+ years college experience, age 21-23 at draft
- May struggle if age > 24 (older prospect)

### Calculation:
```python
def calculate_experience_score(prospect, position):
    """
    Calculate experience and age score.
    """
    college_years = prospect.years_at_college
    age_at_draft = prospect.age_at_draft
    
    # Position-specific expectations
    optimal_years = get_optimal_years(position)
    optimal_age_range = get_optimal_age(position)
    
    # Years score
    if college_years < optimal_years - 1:
        years_score = 30 + (college_years * 10)  # Young, less developed
    elif college_years in optimal_years:
        years_score = 90  # Sweet spot
    else:
        years_score = 70  # More experience, less upside
    
    # Age score
    if optimal_age_range[0] <= age_at_draft <= optimal_age_range[1]:
        age_score = 90
    elif age_at_draft < optimal_age_range[0]:
        age_score = 70  # Young, needs development
    else:
        age_score = 50 - (age_at_draft - optimal_age_range[1]) * 5  # Old relative to peers
    
    # Combine (60% years, 40% age)
    score = (years_score * 0.6) + (age_score * 0.4)
    return min(100, max(0, score))
```

---

## Position-Specific Adjustments (+/- 0-15 points)

Applied AFTER base score calculation to reflect position-specific concerns.

### Quarterback:
- +10 if P5 school and > 500 pass attempts/season
- +5 if college had pro-style offense
- -10 if mobile QB (less production readiness for traditional role)
- -5 if school known for pro-like passing

### Running Back:
- +10 if > 1000 rushing yards last season
- +5 if versatile (carries + catches > 150 combined)
- -5 if < 100 carries last season (limited sample)

### Wide Receiver:
- +10 if catch rate > 65% and > 50 catches last season
- +5 if P5 school with top passing offense
- -5 if highly dependent on play-action/YAC

### Tight End:
- +10 if > 70 catches last season
- +5 if > 600 yards
- -5 if primarily run-blocking role

### Edge Rusher:
- +10 if > 8 sacks last season
- +5 if > 15 pressures per game
- -5 if < 6 sacks (production questions)

### Cornerback / Safety:
- +10 if > 1.5 INTs/season
- +5 if elite measurables (40-time < 4.45 for CB)
- -5 if coverage-only (no run support)

### Interior DL:
- +10 if versatile (both 3-tech and 5-tech snaps > 30%)
- +5 if strong 2-point stance
- -5 if limited snaps (< 300 plays)

### Linebacker:
- +10 if > 100 tackles and > 5 sacks last season
- +5 if coverage ability evident
- -5 if one-dimensional (run support only)

---

## Score Interpretation

| Score Range | Interpretation | Typical Profile |
|-------------|-----------------|-----------------|
| 85-100 | **Ready Now** | Elite measurables + high college production, immediate impact |
| 70-84 | **Ready with Support** | Solid measurables + good production, may need coaching |
| 55-69 | **Development Prospect** | Mixed profile, needs NFL development time |
| 40-54 | **Project Player** | Concerning gaps, development priority |
| 0-39 | **High Risk/Red Flag** | Major concerns, low draft priority |

---

## Confidence Score

Confidence in prediction based on data completeness.

```python
def calculate_confidence(prospect):
    """
    Confidence in production readiness prediction.
    0-100 scale.
    """
    missing_fields = count_missing_measurables(prospect)
    college_games_played = prospect.games_played
    
    # Base confidence: full data = 95
    confidence = 95
    
    # Reduce for missing measurables
    confidence -= missing_fields * 5  # -5 per missing field
    
    # Reduce for low sample size
    if college_games_played < 10:
        confidence -= 20
    elif college_games_played < 20:
        confidence -= 10
    
    return max(40, confidence)  # Minimum 40% confidence
```

---

## Example Calculation

**Prospect: Drake Maye, Quarterback**
- Height: 6'3" (95th %ile for QB)
- Weight: 222 lbs (85th %ile)
- 40-time: 4.78s (60th %ile)
- Vertical: 31" (75th %ile)
- Broad: 10'4" (80th %ile)
- **Measurables Score: 79**

**College Production (UNC):**
- Pass Attempts: 560/season (90th %ile)
- Completion %: 65% (80th %ile)
- TD:INT Ratio: 2.8:1 (85th %ile)
- P5 School: Yes (bonus +5)
- **Production Score: 85**

**Age/Experience:**
- College Years: 2 (less than optimal 3)
- Age at Draft: 21 (optimal)
- **Experience Score: 75**

**Base Score:**
(79 × 0.40) + (85 × 0.40) + (75 × 0.20) = 31.6 + 34 + 15 = **80.6**

**Position Adjustment:**
+10 (P5 + elite production) = **90.6 → 91**

**Final Score: 91 - Ready Now** ✅
**Confidence: 95%** (all data available)

---

## Implementation Checklist

- [ ] Database: Add `production_readiness_score` column to `prospects` table
- [ ] Feature engineering: Implement position-specific metric calculations
- [ ] Scoring: Implement all 3 components + adjustments
- [ ] Caching: Cache scores (recalculate if new data arrives)
- [ ] Testing: Compare to historical draft positions (validation)
- [ ] Endpoint: `GET /api/analytics/production-readiness/:prospect_id`
- [ ] Response includes: score, confidence, key factors, percentile
- [ ] Documentation: User guide explaining methodology
- [ ] Monitoring: Track prediction accuracy over time

---

## Future Enhancements (Post-Launch)

- [ ] ML model refinement with actual production data
- [ ] Per-team evaluation adjustments
- [ ] Injury history incorporation (when available)
- [ ] Scheme fit adjustments (offensive/defensive scheme)
- [ ] Video analysis integration

---

**Next Steps:** PO to review and confirm formula. Ready for Sprint 5 implementation.

