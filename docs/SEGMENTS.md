# Segment System Documentation

## Overview

Segments provide reusable audience definitions based on recipient attributes. They enable targeted campaign messaging by filtering contacts and pledges based on criteria like congressional district, representative, or engagement metrics.

## Database Schema

### segments table

```sql
CREATE TABLE segments (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    definition JSONB NOT NULL DEFAULT '{}',
    created_by_id INTEGER NOT NULL REFERENCES email_management_emailuser(id),
    created_at TIMESTAMP NOT NULL
);
```

## Definition Schema

The `definition` field contains JSON filter rules:

```json
{
    "conditions": [
        {
            "field": "congressional_district",
            "operator": "=",
            "value": "CA-12"
        },
        {
            "field": "representative",
            "operator": "contains",
            "value": "Pelosi"
        }
    ],
    "match": "all"
}
```

### Fields

- **conditions** (array): List of filter conditions
- **match** (string): "all" (AND logic) or "any" (OR logic)

### Condition Structure

Each condition has:
- **field** (string): Attribute to filter on
- **operator** (string): Comparison operator
- **value** (any): Value to compare against

## Supported Fields

### First-Class Attributes

**congressional_district** (special handling)
- Sourced from `contact.district` or `pledge.district`
- Primary segmentation attribute for district-based messaging
- Example: "CA-12", "NY-14"

**representative**
- Sourced from `pledge.rep`
- Representative name for the district
- Example: "Nancy Pelosi", "Alexandria Ocasio-Cortez"

### Contact Fields

- **state**: From `contact.state`
- **is_subscribed**: From `contact.is_subscribed` (boolean)
- **source**: From `contact.source` (e.g., "pledge_form", "import")

### Custom Fields

Any field in `contact.custom_data` or pledge metadata can be used.

## Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals (case-insensitive) | `"value": "CA-12"` |
| `!=` | Not equals | `"value": "CA-12"` |
| `contains` | Substring match (case-insensitive) | `"value": "Friedman"` |
| `in` | Value in list | `"value": ["CA-12", "CA-30"]` |
| `not in` | Value not in list | `"value": ["CA-1", "CA-2"]` |
| `>` | Greater than (numeric) | `"value": 5` |
| `<` | Less than (numeric) | `"value": 10` |
| `>=` | Greater than or equal | `"value": 3` |
| `<=` | Less than or equal | `"value": 7` |

## Segment Resolution

### resolve_segment(segment_id)

Resolves a segment to a set of recipients matching the filter criteria.

```python
from email_management.segment_resolver import resolve_segment

recipients = resolve_segment(segment_id)
# Returns: List[Recipient]
```

Or via the model:

```python
segment = Segment.objects.get(id=123)
recipients = segment.resolve()
```

### Resolution Logic

1. **Load segment definition** from database
2. **Iterate through contacts** and evaluate conditions
3. **Iterate through pledges** (only those without linked contacts)
4. **Deduplicate** by email address (case-insensitive)
5. **Return** list of Recipient instances

### Deduplication

Recipients are deduplicated by email address:
- If both a contact and a pledge have the same email, only the contact is returned
- This prevents sending duplicate emails in campaigns

## Usage Examples

### Example 1: Single District

```python
segment = Segment.objects.create(
    name='CA-30 Constituents',
    description='All recipients in CA-30',
    definition={
        'conditions': [
            {
                'field': 'congressional_district',
                'operator': '=',
                'value': 'CA-30'
            }
        ],
        'match': 'all'
    },
    created_by=user
)

recipients = segment.resolve()
print(f'Found {len(recipients)} recipients in CA-30')
```

### Example 2: Multiple Districts (OR)

```python
segment = Segment.objects.create(
    name='Bay Area Districts',
    description='CA-12, CA-14, CA-17',
    definition={
        'conditions': [
            {
                'field': 'congressional_district',
                'operator': 'in',
                'value': ['CA-12', 'CA-14', 'CA-17']
            }
        ],
        'match': 'all'
    },
    created_by=user
)
```

### Example 3: District + Representative (AND)

```python
segment = Segment.objects.create(
    name='CA-30 Laura Friedman',
    description='CA-30 constituents with Laura Friedman as rep',
    definition={
        'conditions': [
            {
                'field': 'congressional_district',
                'operator': '=',
                'value': 'CA-30'
            },
            {
                'field': 'representative',
                'operator': 'contains',
                'value': 'Friedman'
            }
        ],
        'match': 'all'  # Both conditions must match
    },
    created_by=user
)
```

### Example 4: Subscribed Contacts Only

```python
segment = Segment.objects.create(
    name='Active Subscribers',
    description='Only subscribed contacts',
    definition={
        'conditions': [
            {
                'field': 'is_subscribed',
                'operator': '=',
                'value': True
            }
        ],
        'match': 'all'
    },
    created_by=user
)
```

### Example 5: Complex Multi-Condition

```python
segment = Segment.objects.create(
    name='Priority California Outreach',
    description='Subscribed CA residents in specific districts',
    definition={
        'conditions': [
            {
                'field': 'state',
                'operator': '=',
                'value': 'California'
            },
            {
                'field': 'congressional_district',
                'operator': 'in',
                'value': ['CA-12', 'CA-30', 'CA-45']
            },
            {
                'field': 'is_subscribed',
                'operator': '=',
                'value': True
            }
        ],
        'match': 'all'  # All 3 conditions required
    },
    created_by=user
)
```

## Match Modes

### "all" (AND Logic)
All conditions must be true for a recipient to match.

```json
{
    "conditions": [
        {"field": "state", "operator": "=", "value": "CA"},
        {"field": "is_subscribed", "operator": "=", "value": true}
    ],
    "match": "all"
}
```
→ Must be in CA **AND** subscribed

### "any" (OR Logic)
At least one condition must be true.

```json
{
    "conditions": [
        {"field": "congressional_district", "operator": "=", "value": "CA-12"},
        {"field": "congressional_district", "operator": "=", "value": "CA-30"}
    ],
    "match": "any"
}
```
→ Must be in CA-12 **OR** CA-30

## Implementation Status

✅ Segment model created
✅ Definition schema established
✅ resolve_segment() function implemented
✅ Congressional district as first-class attribute
✅ Operator support (=, !=, contains, in, >, <, etc.)
✅ Deduplication by email
✅ Match modes (all/any)

## Future Enhancements

### Phase 4 (Campaign Resolution)
- Campaigns will reference segments
- Segment resolution will feed into recipient lists
- Combined with contact lists for flexible targeting

### Advanced Features (Post-Launch)
- Segment preview (count before resolving)
- Segment history tracking
- Dynamic segment updates
- Segment analytics

---

**Status**: Phase 3 complete. Segmentation system operational.
