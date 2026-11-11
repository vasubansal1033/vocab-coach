You write one "choose the word" recognition item for vocab-coach.

Given a precision group (one vague head lemma in one sense, with precise options), invent
a short workplace or everyday situation and one sentence with a single blank where the
user must pick which option fits best.

Rules:
- `situation` is one sentence that sets the scene. It must not contain any of the options.
- `sentence` is one natural sentence with exactly one blank written as `___`.
  Do not put any precise option words in the sentence.
- Provide four to six `candidates`. Use only `option_id` values from the list below.
- Exactly one candidate must have `best: true`. That option must be the clear best fit.
- Every candidate needs `fit` of `fits`, `partly`, or `wrong`, plus a one-line `reason`.
  The best candidate should have `fit: fits`. Other candidates that could work in a stretch
  may be `partly`; clear mismatches are `wrong`.
- Write so a careful reader would mark the best option and reject the wrong ones.

Return JSON only with keys: situation, sentence, candidates.
Each candidate object has keys: option_id, fit, reason, best.

Group id: {{ group.id }}
Head lemma: {{ group.head_lemma }} ({{ group.pos }})
Sense: {{ group.sense_gloss }}

Options:
{% for opt in group.options %}
- id={{ opt.id }} word="{{ opt.word }}": {{ opt.distinction }}
{% endfor %}
