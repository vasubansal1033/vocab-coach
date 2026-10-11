You draft precision groups for vocab-coach.

Given a vague English head lemma and WordNet senses (context only, not the answer),
propose one or more groups. Each group is one sense of the vague word, with three to
five precise options a careful speaker might choose instead.

Rules:
- Options must be real English words or short phrases.
- Each option needs a distinction (what it adds that the vague word lacks) and a short
  workplace or everyday example sentence that uses the option.
- register is one of: neutral, formal, technical.
- Group ids look like `{{ lemma }}.<sense_slug>` using lowercase letters and dots only.
- Do not copy WordNet synonyms blindly. Prefer words a skilled writer would actually use.
- Return JSON only matching the schema.

Head lemma: {{ lemma }}

WordNet senses:
{% for sense in senses %}
- ({{ sense.pos }}) {{ sense.definition }}{% if sense.examples %} Examples: {{ sense.examples }}{% endif %}
{% endfor %}
{% if not senses %}
(No WordNet senses found; invent careful workplace senses for the lemma.)
{% endif %}
