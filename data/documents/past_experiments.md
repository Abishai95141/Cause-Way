# Past Experiments Archive

## EXP-2024-Q4-001: Holiday Season Promotion Impact

**Experiment Period**: November 15 - December 31, 2024  
**Hypothesis**: Running a 25% discount during Black Friday would increase conversions without cannibalizing full-price sales.

**Results**:
- Conversion rate increased 45% during promo period
- However, 60% of new signups churned within 30 days (vs. baseline 25%)
- Net revenue impact was -12% due to discount + churn
- **Conclusion**: Seasonal confounding is significant during retail events. Customers acquired during heavy discounting periods have lower LTV.

**Recommendation**: Avoid running experiments during major retail events (Black Friday, Cyber Monday, Christmas). Best window for clean measurement: mid-January to mid-February.

---

## EXP-2024-Q3-002: Trial Duration Optimization

**Experiment Period**: August 1 - September 30, 2024  
**Hypothesis**: Reducing trial from 14 days to 7 days will increase urgency and improve conversion rates.

**Results**:
- 7-day trial: 18% trial-to-paid conversion
- 14-day trial: 22% trial-to-paid conversion
- 7-day had 15% lower activation rate (users didn't explore features)
- **Conclusion**: Shorter trial increases urgency but reduces product exploration. Optimal trial length depends on product complexity.

**Confounders Identified**:
- Concurrent A/B test on onboarding flow contaminated results
- Support ticket volume was unusually high due to unrelated bug
- **Learning**: Always check for concurrent changes before analyzing results.

---

## EXP-2024-Q2-003: Pricing Tier Restructuring

**Experiment Period**: May 1 - June 30, 2024  
**Hypothesis**: Simplifying from 5 tiers to 3 tiers will reduce decision paralysis and increase conversions.

**Results**:
- Conversion rate increased 12%
- Average deal size decreased 8%
- Enterprise tier adoption increased 25%
- **Net impact**: +5% monthly revenue

**Key Insights**:
- Price changes take 2-3 billing cycles to fully manifest
- Cannot measure pricing impact accurately if other funnel changes happen within 14 days
- **Rule**: Wait minimum 14 days after any pricing change before measuring unrelated metrics.

---

## EXP-2024-Q1-004: Customer Support Chatbot Launch

**Experiment Period**: February 1 - March 31, 2024  
**Hypothesis**: AI chatbot can handle 40% of support tickets, reducing cost per ticket.

**Results**:
- Chatbot handled 52% of initial queries
- However, 35% of chatbot interactions escalated to human
- Net cost reduction: 22%
- NPS improved by 8 points (faster initial response)

**Causal Notes**:
- Support metrics are lagging indicators for product changes
- Changes to support SLA affect churn with 30-60 day delay
- Any support change confounds churn measurements for 2 months.

---

## Experiment Design Best Practices

### Minimum Washout Periods
| Change Type | Washout Days |
|-------------|--------------|
| Pricing | 14 days |
| Onboarding | 21 days |
| Support SLA | 60 days |
| Marketing Campaign | 30 days |

### Confounder Checklist Before Any Experiment
1. ☐ Check company_changes.json for last 14 days
2. ☐ Verify no concurrent A/B tests on overlapping metrics
3. ☐ Confirm no major product releases scheduled
4. ☐ Review marketing calendar for campaigns
5. ☐ Check support ticket volume baseline
