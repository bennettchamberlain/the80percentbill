# Rep Narrative Content — Design Spec

## Overview

Generate a 3-5 paragraph storytelling narrative for each of the 538 members of Congress, written through the lens of the 80% Bill. Each narrative is factually rigorous but delivered with a satirical, pointed tone — think well-researched political satire where the contradictions speak for themselves.

## Data Model Changes

Add two fields to `Representative` in `reps/models.py`:

```python
narrative = models.TextField(blank=True, default="")
narrative_updated = models.DateTimeField(null=True, blank=True)
```

- `narrative`: The generated text (plain text with paragraph breaks)
- `narrative_updated`: Timestamp of last generation, so we know how stale it is

Migration required after adding these fields.

## Detail Page Changes

Add a "The Story" section to `reps/templates/reps/detail.html`, inserted immediately after the `rep-header-card` div and **before** the alignment score `rep-section` div (i.e., before line 23 in the current template):

```html
<div class="rep-section">
    <h2>The Story</h2>
    {% if rep.narrative %}
    <div class="rep-narrative">
        {{ rep.narrative|linebreaks }}
    </div>
    {% else %}
    <div class="note-text">Profile narrative coming soon.</div>
    {% endif %}
</div>
```

No new CSS needed — uses existing `.rep-section` and `.note-text` styles. The `linebreaks` template filter converts plain text paragraphs to `<p>` tags.

## Workflow: Claude Code Scheduled Task

### How it works

A repeatable Claude Code workflow that processes representatives one state at a time. Each run:

1. Reads the prompt template from `reps/prompts/narrative_prompt.md`
2. Queries the database for reps in the target state that don't have a narrative yet
3. For each rep:
   a. Gathers their data from the DB (name, party, district, social media, OpenSecrets ID, etc.)
   b. Does web searches to research their positions on the 20 bill topics
   c. Writes the narrative following the prompt template's instructions
   d. Saves the narrative and timestamp to the database via Django shell:
      ```bash
      cd /Users/adamlinssen/Desktop/the80percentbill
      DJANGO_SETTINGS_MODULE=the_80_percent_bill.settings DEBUG=true python3 -c "
      import django; django.setup()
      from django.utils import timezone
      from reps.models import Representative
      rep = Representative.objects.get(bioguide_id='XXXX')
      rep.narrative = '''...generated text...'''
      rep.narrative_updated = timezone.now()
      rep.save(update_fields=['narrative', 'narrative_updated'])
      "
      ```
4. Reports how many narratives were generated

### Batch structure

- **One state per run** — California has 54 reps, Alaska has 3
- **Resumable** — only processes reps with empty `narrative` fields
- **Selective** — can target a single rep by bioguide ID for rewrites (pass `--bioguide-id=XXXX` to overwrite an existing narrative)
- **Anyone can run it** — just invoke the scheduled task or run the workflow manually in Claude Code

### Prompt template

Lives at `reps/prompts/narrative_prompt.md` so anyone on the team can adjust the tone and instructions without touching code.

The prompt includes:
- The rep's database fields (name, party, state, district, etc.)
- The full list of 20 bill articles (read directly from `bill/articles.py` which exports an `ARTICLES` list of tuples: `(title, description, link, note, skip_numbering?)`)
- Research instructions (what to search for)
- Writing instructions (tone, structure, sourcing rules)

### Tone guide (embedded in prompt)

Write like a well-researched political satirist. The facts are sacred — never exaggerate or fabricate. But how you present those facts can be pointed, ironic, and occasionally biting. If a rep talks about fighting corruption while their top donor is a corporate PAC, let the irony land. Don't editorialize with opinions — let the contradictions speak for themselves.

Imagine you're a journalist writing a fair but unflinching profile. The reader should walk away understanding where this person stands and why.

### Research targets per rep

The workflow searches for:
- Cosponsorship and voting history on the 20 bills (or closely related legislation)
- Top campaign donors via OpenSecrets
- Committee assignments
- Notable public statements on the 80% Bill topics
- Any contradictions between stated positions and donor interests

If information can't be found on a topic, skip it — don't speculate.

## Files to create

- `reps/prompts/narrative_prompt.md` — The prompt template
- `.claude/scheduled-tasks/generate-rep-narratives/SKILL.md` — The scheduled task definition

## Files to modify

- `reps/models.py` — Add `narrative` and `narrative_updated` fields
- `reps/templates/reps/detail.html` — Add "The Story" section
- `reps/admin.py` — Add `narrative` to `readonly_fields` and `search_fields` (do NOT add to `list_display` — it's too large for the list view). Make it editable in admin only if someone needs to manually blank it for a rewrite.
- New migration file (auto-generated)

## Progress tracking

To see which states are done:

```sql
SELECT state, COUNT(*) as total,
       SUM(CASE WHEN narrative != '' THEN 1 ELSE 0 END) as done
FROM reps_representative
WHERE in_office = 1
GROUP BY state ORDER BY state;
```

## Out of scope (for now)

- Alignment score computation (separate feature)
- Per-bill position tracking in `BillPosition` model (separate feature)
- Automated fact-checking of generated narratives
- User-facing editing interface for narratives
