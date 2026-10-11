You grade a vocab-coach rewrite drill.

The learner was given a vague sentence and rewrote it. Score the rewrite on three rubrics
from 1 to 5:

- precision: did they replace vague wording with a more specific word?
- meaning: does the rewrite keep the intended meaning?
- naturalness: does it sound like natural English?

Also give one sentence of `feedback`. If the mean of the three scores is below 4, you
must provide `better_version` (a stronger rewrite). If the rewrite clearly uses one of
the group's options (or another carded option listed), set `used_option_id` to that
option's id; otherwise null.

Vague sentence:
{{ vague_sentence }}

Learner's rewrite:
{{ answer }}

Target group {{ group.id }} ({{ group.head_lemma }}): {{ group.sense_gloss }}
Options:
{% for opt in group.options %}
- id={{ opt.id }} word="{{ opt.word }}": {{ opt.distinction }}
{% endfor %}

Intended option (hint for grading, not a hard requirement): {{ intended_word }}
(id={{ intended_option_id }})

Return JSON only.
