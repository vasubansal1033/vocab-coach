You write one compare practice item for vocab-coach.

Given a word set of near-synonyms (usually a confusable set) and an item_type,
write either a pair item or a misuse item. Focus on workplace English.

Item type requested: {{ item_type }}

## If item_type is compare_pair

Return JSON with key `sentences`: a list of exactly two objects.
Each object has:
- `text`: one natural sentence with exactly one blank written as `___`
- `fits_option_id`: the only option from the set that correctly fills that blank

Rules:
- The two sentences must fit two different option_ids.
- Do not put any of the option words in the sentence text outside the blank.
- A careful reader who knows the distinctions should get both blanks right.
- Use only option_id values from the list below.

## If item_type is compare_misuse

Return JSON with keys:
- `sentence`: one complete sentence that wrongly uses one word from the set
- `misused_option_id`: the option_id of the word that was used wrongly
- `replacement_option_id`: the option_id that should replace it
- `reason`: one short line explaining the mix-up

Rules:
- The misused word must appear in the sentence in a natural surface form.
- misused_option_id and replacement_option_id must differ.
- Use only option_id values from the list below.

Return JSON only. Do not invent other keys.

Group id: {{ group.id }}
Kind: {{ group.kind }}
{% if group.head_lemma %}Head lemma: {{ group.head_lemma }}
{% endif %}POS: {{ group.pos }}
Sense: {{ group.sense_gloss }}

Options:
{% for opt in group.options %}
- id={{ opt.id }} word="{{ opt.word }}": {{ opt.distinction }}
{% endfor %}
