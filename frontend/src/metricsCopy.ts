/** Dashboard metric definitions from docs/DESIGN.md "Metrics". */

export const METRIC_DEFINITIONS = {
  crutchRate:
    '1000 × (crutch-list lemma uses in your messages) ÷ (total words). Lower is better.',
  acceptance:
    'Suggestions you accepted ÷ suggestions shown. A low rate often points at editor quality, not at you.',
  spontaneous:
    'Accepted options that later appear in an unprompted, correct use within 30 days ÷ options accepted in the window.',
  misuse:
    'Incorrect non-idiom word_used events ÷ all non-idiom word_used events. Idioms are counted separately.',
  idiomMisuse:
    'Incorrect idiom word_used events ÷ all idiom word_used events. Misused idioms read worse than plain words.',
  mtld:
    'Lexical diversity (MTLD). Forward and backward passes averaged; shown only when the window has at least 100 words.',
  overuseLift:
    'For surface words with at least five uses: (your rate) ÷ wordfreq English rate. High lift means you use it far more than typical English.',
  drillScore: 'Mean rewrite-drill score per week (precision, meaning, and naturalness, each 1 to 5).',
} as const
