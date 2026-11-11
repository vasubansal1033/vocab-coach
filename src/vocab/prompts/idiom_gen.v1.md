You draft everyday idiom sets for vocab-coach.

Given a plain head lemma (the word the idioms can replace), propose one idiom
group of two to four workplace idioms that express that meaning.

Rules:
- kind is always idiom; head_lemma is the plain word (for example agree).
- Group id looks like `idiom.<head_lemma>` (for example `idiom.agree`).
- Option word is the idiom in base form ("cut corners", "see eye to eye").
  Do not use pronoun slots such as "pull one's weight"; those do not match.
- Each option needs distinction, example, register, and details with meaning,
  tier (everyday for this draft), region (common, uk, or us), variants,
  misuse_example, and avoid_when. Leave origin empty for everyday idioms.
- Do not copy published dictionary entries. Write original examples.
- Return JSON only matching the schema.

Head lemma: {{ lemma }}
