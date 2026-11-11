You write one rewrite drill for vocab-coach.

Given a precision group (one vague head lemma in one sense, with precise options), invent
a short workplace or everyday situation and one natural vague sentence for it. The
sentence should use the vague head lemma (or a close surface form) so that exactly one
of the options is the best fit by a clear margin.

Rules:
- `context` is one or two sentences that set the situation before the vague sentence.
  It must not contain any of the precise options.
- The vague sentence must sound like something a person would actually say or write.
- Prefer the intended option from the list; set `intended_option_id` and `intended_word`
  to that option.
- Do not use any of the precise options in the context or the vague sentence.
- Write so a careful reader would pick the intended option over the others by a clear
  margin; the other options should be clearly weaker fits for this situation.
- Return JSON only with keys: context, vague_sentence, intended_option_id, intended_word.

Group id: {{ group.id }}
Head lemma: {{ group.head_lemma }} ({{ group.pos }})
Sense: {{ group.sense_gloss }}

Options:
{% for opt in group.options %}
- id={{ opt.id }} word="{{ opt.word }}": {{ opt.distinction }}
{% endfor %}
