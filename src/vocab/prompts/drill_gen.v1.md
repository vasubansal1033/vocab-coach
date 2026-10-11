You write one rewrite drill for vocab-coach.

Given a precision group (one vague head lemma in one sense, with precise options), invent
one natural vague sentence from a workplace or everyday context. The sentence should use
the vague head lemma (or a close surface form) so that exactly one of the options is the
best fit by a clear margin.

Rules:
- The sentence must sound like something a person would actually say or write.
- Prefer the intended option from the list; set `intended_option_id` and `intended_word`
  to that option.
- Do not use any of the precise options in the vague sentence itself.
- Return JSON only.

Group id: {{ group.id }}
Head lemma: {{ group.head_lemma }} ({{ group.pos }})
Sense: {{ group.sense_gloss }}

Options:
{% for opt in group.options %}
- id={{ opt.id }} word="{{ opt.word }}": {{ opt.distinction }}
{% endfor %}
