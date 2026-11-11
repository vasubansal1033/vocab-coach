You write one practice item for vocab-coach.

Given a word set and an item_type, write the matching JSON. Focus on workplace English.
Do not invent option_id values; use only ids from the group below when a field needs one.

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

## If item_type is idiom_recognise

Return JSON with keys:
- `paragraph`: two or three short workplace sentences that naturally use exactly one idiom from the set
- `option_id`: the option_id of the idiom that appears in the paragraph
- `choices`: three or four objects `{id, label}` where `id` is an option_id from the set when possible, or a short distractor id such as `distract:0` with a plausible wrong idiom phrase as `label`

Rules:
- The target idiom must appear in the paragraph in a natural surface form.
- Exactly one choice `id` equals `option_id`.
- Distractor labels must be real-looking idiom phrases, not nonsense.
- Use only real option_id values for the correct choice.

## If item_type is idiom_meaning

Return JSON with keys:
- `option_id`: which idiom is being tested (must be from the set)
- `choices`: three or four `{id, label}` meaning statements
- `correct_id`: the id of the choice that matches the idiom's true meaning

Rules:
- One choice must match the idiom's meaning closely; the others are plausible wrong meanings.
- Choice ids may be short strings such as `c0`, `c1`.
- Do not put the idiom phrase itself in the choice labels.

## If item_type is idiom_situation

Return JSON with keys:
- `option_id`: which idiom is being tested (must be from the set)
- `choices`: three or four `{id, label}` short workplace situations
- `correct_id`: the id of the situation where the idiom fits best

Rules:
- Exactly one situation should clearly fit the idiom; the others should not.
- Respect the idiom's avoid_when: do not mark a forbidden situation as correct.
- Choice ids may be short strings such as `s0`, `s1`.

Return JSON only. Do not invent other keys.

Group id: {{ group.id }}
Kind: {{ group.kind }}
{% if group.head_lemma %}Head lemma: {{ group.head_lemma }}
{% endif %}POS: {{ group.pos }}
Sense: {{ group.sense_gloss }}

Options:
{% for opt in group.options %}
- id={{ opt.id }} word="{{ opt.word }}": {{ opt.distinction }}
{% if opt.details %}  details={{ opt.details }}
{% endif %}
{% endfor %}
