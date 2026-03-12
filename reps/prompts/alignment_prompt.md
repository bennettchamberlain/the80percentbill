# 80% Bill Alignment Grading Rubric

You are grading a batch of congressional representatives on their alignment with the 80% Bill — a package of 20 popular, bipartisan policy proposals.

## The 20 Bill Articles

1. Ban Congressional Stock Trading
2. End Forever Wars
3. Lifetime Lobbying Ban
4. Tax the Ultra-Wealthy
5. Ban Corporate PACs
6. Audit the Pentagon
7. Medicare Drug Negotiation
8. Fair Elections & End Gerrymandering
9. Protect US Farmland
10. Ban Corporate Purchase of Single Family Homes
11. Fund Social Security
12. Police Body Cameras
13. Ban 'Dark Money' (Overturn Citizens United)
14. Paid Family Leave
15. Release the Epstein Files
16. The DISCLOSE Act
17. Close Tax Loopholes
18. Right to Repair (Ban 'Parts Pairing')
19. Ban Junk Fees
20. Congressional Term Limits

## Position Criteria

For each of the 20 articles, assign ONE position:

| Position | Criteria | Points |
|----------|----------|--------|
| `sponsor` | Introduced or lead-sponsored the bill or near-identical legislation | 1 |
| `cosponsor` | Cosponsored the bill or near-identical legislation | 1 |
| `voted_yes` | Voted in favor, publicly championed, took concrete supportive action | 1 |
| `voted_no` | Voted against, actively blocked, publicly opposed | 0 |
| `no_position` | No clear evidence in the narrative | 0 |

## Scoring

`alignment_score` = count of articles where position is `sponsor`, `cosponsor`, or `voted_yes` (max 20).

## Grading Rules

1. Grade on stated positions and votes described in the narrative, not donor influence
2. If the narrative doesn't mention a topic → `no_position`
3. Rhetorical-only support (public statements, press releases) → `voted_yes` (benefit of the doubt, first pass)
4. Opposition to the concept → `voted_no` even without a literal floor vote
5. No position = 0 points. Absence of evidence is meaningful.

## Output Format

Return a JSON object keyed by bioguide_id:

```json
{
    "B000574": {
        "score": 14,
        "positions": {
            "1": "cosponsor",
            "2": "no_position",
            "3": "voted_yes",
            ...
        }
    },
    ...
}
```

Every rep must have exactly 20 position entries (keys "1" through "20").
The score must equal the count of positions that are sponsor/cosponsor/voted_yes.
