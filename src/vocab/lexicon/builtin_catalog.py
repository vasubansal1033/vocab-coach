"""Built-in lexicon catalog for admin API import (not YAML).

Former data/precision_groups content. Runtime never reads seed files from disk.
"""

from __future__ import annotations

from typing import Any

BUILTIN_LEXICON_ITEMS: list[dict[str, Any]] = [
    {
        "kind": "precision",
        "head_lemma": "bad",
        "groups": [
            {
                "id": "bad.quality",
                "pos": "ADJ",
                "sense_gloss": "of poor quality or undesirable",
                "options": [
                    {
                        "word": "flawed",
                        "distinction": "has a specific defect you can point to",
                        "example": "The proposal is flawed because it ignores rollback.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "poor",
                        "distinction": "below an expected standard overall",
                        "example": "The documentation is poor and leaves out setup steps.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "deficient",
                        "distinction": "missing something required",
                        "example": "The test suite is deficient in failure cases.",
                        "register": "formal",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "big",
        "groups": [
            {
                "id": "big.scale",
                "pos": "ADJ",
                "sense_gloss": "large in size, degree, or importance",
                "options": [
                    {
                        "word": "large",
                        "distinction": "high in quantity or physical size",
                        "example": "We need a large buffer for peak traffic.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "major",
                        "distinction": "important enough to change plans",
                        "example": "This is a major change to the auth flow.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "substantial",
                        "distinction": "considerable in amount or impact",
                        "example": "We saw a substantial drop in error rate.",
                        "register": "formal",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.affect-impact",
                "pos": "VERB",
                "sense_gloss": "to influence something, with impact often implying a stronger or "
                "measurable effect",
                "options": [
                    {
                        "word": "affect",
                        "distinction": "to influence or change something, the default verb for "
                        "this sense",
                        "example": "The outage affected three regional customers.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["affect performance", "adversely affect"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                    {
                        "word": "impact",
                        "distinction": "to have a strong or noticeable effect; more emphatic, "
                        "and some readers dislike it as a verb",
                        "example": "The pricing change impacted renewal rates in the enterprise "
                        "tier.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["impact revenue", "negatively impact"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.annoyed-irritated-exasperated-livid",
                "pos": "ADJ",
                "sense_gloss": "degrees of anger from mild bother to extreme fury",
                "options": [
                    {
                        "word": "annoyed",
                        "distinction": "mildly bothered by something small",
                        "example": "I was annoyed that the meeting started ten minutes late.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["annoyed by", "slightly annoyed"],
                            "connotation": "negative",
                            "strength": 1,
                        },
                    },
                    {
                        "word": "irritated",
                        "distinction": "more sharply bothered; the feeling lasts and frays "
                        "patience",
                        "example": "She grew irritated by the repeated context switches.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["irritated by", "clearly irritated"],
                            "connotation": "negative",
                            "strength": 2,
                        },
                    },
                    {
                        "word": "exasperated",
                        "distinction": "worn out by something that keeps happening; patience is "
                        "spent",
                        "example": "He was exasperated after the third rollback of the same "
                        "change.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["exasperated by", "thoroughly exasperated"],
                            "connotation": "negative",
                            "strength": 3,
                        },
                    },
                    {
                        "word": "livid",
                        "distinction": "extremely angry; far stronger than everyday workplace "
                        "frustration",
                        "example": "The client was livid when the outage hit during their launch.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["livid about", "absolutely livid"],
                            "connotation": "negative",
                            "strength": 4,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.assure-ensure",
                "pos": "VERB",
                "sense_gloss": "calming a person with a promise versus making an outcome certain",
                "options": [
                    {
                        "word": "assure",
                        "distinction": "you tell someone so they feel confident; the object is "
                        "a person",
                        "example": "I assured the client that the patch would ship by Friday.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["assure someone that", "rest assured"],
                            "connotation": "positive",
                            "strength": None,
                        },
                    },
                    {
                        "word": "ensure",
                        "distinction": "you take steps so that something happens; the object is "
                        "a result",
                        "example": "Please ensure the backup completes before the cutover.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["ensure that", "ensure compliance"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.comprise-compose",
                "pos": "VERB",
                "sense_gloss": "the whole contains its parts versus the parts make up the whole",
                "options": [
                    {
                        "word": "comprise",
                        "distinction": 'the whole comprises its parts (avoid "is comprised of" '
                        "in careful writing)",
                        "example": "The working group comprises six engineers and one product "
                        "manager.",
                        "register": "formal",
                        "details": {
                            "collocations": ["comprise", "comprising"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                    {
                        "word": "compose",
                        "distinction": 'the parts compose the whole; "is composed of" is the '
                        "common passive",
                        "example": "The panel is composed of reviewers from three teams.",
                        "register": "formal",
                        "details": {
                            "collocations": ["composed of", "compose the"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.continual-continuous",
                "pos": "ADJ",
                "sense_gloss": "repeated over time versus unbroken without a pause",
                "options": [
                    {
                        "word": "continual",
                        "distinction": "happening again and again, with gaps between events",
                        "example": "Continual status pings made it hard to focus on deep work.",
                        "register": "formal",
                        "details": {
                            "collocations": ["continual interruptions", "continual updates"],
                            "connotation": "negative",
                            "strength": None,
                        },
                    },
                    {
                        "word": "continuous",
                        "distinction": "going on without a break for a stretch of time",
                        "example": "The continuous deploy pipeline ran for six hours overnight.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["continuous process", "continuous monitoring"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.fewer-less",
                "pos": "DET",
                "sense_gloss": "countable items versus uncountable amounts",
                "options": [
                    {
                        "word": "fewer",
                        "distinction": "use with countable nouns you can number",
                        "example": "We logged fewer critical incidents this quarter than last.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["fewer than", "fewer errors"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                    {
                        "word": "less",
                        "distinction": "use with uncountable amounts, or with singular mass nouns",
                        "example": "The new cache uses less memory under peak load.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["less than", "less time"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.imply-infer",
                "pos": "VERB",
                "sense_gloss": "a speaker or text suggests something versus a listener draws a "
                "conclusion",
                "options": [
                    {
                        "word": "imply",
                        "distinction": "the speaker or text suggests something without stating "
                        "it outright",
                        "example": "Her silence implies that the plan failed.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["imply that", "seem to imply"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                    {
                        "word": "infer",
                        "distinction": "the listener or reader draws a conclusion from evidence",
                        "example": "From the error logs we inferred a race condition.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["infer from", "infer that"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.persuade-convince",
                "pos": "VERB",
                "sense_gloss": "getting someone to act versus getting someone to believe",
                "options": [
                    {
                        "word": "persuade",
                        "distinction": "you get someone to do something, often by argument or "
                        "appeal",
                        "example": "She persuaded the team to ship the smaller release first.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["persuade someone to", "try to persuade"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                    {
                        "word": "convince",
                        "distinction": "you get someone to accept that something is true",
                        "example": "The benchmark data convinced him that the rewrite was worth "
                        "it.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["convince someone that", "convince of"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.principal-principle",
                "pos": "NOUN",
                "sense_gloss": "a main person or sum of money versus a rule or belief",
                "options": [
                    {
                        "word": "principal",
                        "distinction": "the main person in a role, or the capital sum of a loan",
                        "example": "The principal on the loan falls due next March.",
                        "register": "formal",
                        "details": {
                            "collocations": ["school principal", "principal amount"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                    {
                        "word": "principle",
                        "distinction": "a guiding rule, belief, or scientific law",
                        "example": "As a matter of principle we do not store plaintext passwords.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["in principle", "principle of"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "confusable",
        "head_lemma": None,
        "groups": [
            {
                "id": "confusable.sceptical-cynical",
                "pos": "ADJ",
                "sense_gloss": (
                    "doubting a claim until evidence appears versus assuming bad motives"
                ),
                "options": [
                    {
                        "word": "sceptical",
                        "distinction": "you withhold belief until you see good evidence",
                        "example": "She was sceptical of the vendor's latency claims until we "
                        "ran our own test.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["sceptical of", "remain sceptical"],
                            "connotation": "neutral",
                            "strength": None,
                        },
                    },
                    {
                        "word": "cynical",
                        "distinction": "you assume people act from self-interest or that ideals "
                        "are a front",
                        "example": "His cynical take was that the roadmap existed only to calm "
                        "investors.",
                        "register": "neutral",
                        "details": {
                            "collocations": ["cynical about", "cynical view"],
                            "connotation": "negative",
                            "strength": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "easy",
        "groups": [
            {
                "id": "easy.difficulty",
                "pos": "ADJ",
                "sense_gloss": "not difficult; requiring little effort",
                "options": [
                    {
                        "word": "simple",
                        "distinction": "few moving parts; easy to understand",
                        "example": "A simple retry fixed most of the flakes.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "straightforward",
                        "distinction": "clear path with no hidden complications",
                        "example": "The deploy steps are straightforward.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "effortless",
                        "distinction": "feels easy in practice once set up",
                        "example": "After the script, rollbacks became effortless.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "fix",
        "groups": [
            {
                "id": "fix.repair",
                "pos": "VERB",
                "sense_gloss": "make a broken or faulty thing work again",
                "options": [
                    {
                        "word": "resolve",
                        "distinction": "the cause is removed, so the problem will not come back",
                        "example": "We resolved the timeout by fixing the connection pool size.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "patch",
                        "distinction": "a targeted change, often quick and possibly temporary",
                        "example": "We patched the parser to skip malformed rows.",
                        "register": "technical",
                        "details": None,
                    },
                    {
                        "word": "work around",
                        "distinction": "the cause remains but is avoided",
                        "example": "We worked around the bug by retrying the request.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "mitigate",
                        "distinction": "the harm is reduced but not removed",
                        "example": "The rate limit mitigates the overload.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "get",
        "groups": [
            {
                "id": "get.obtain",
                "pos": "VERB",
                "sense_gloss": "come to have or receive something",
                "options": [
                    {
                        "word": "obtain",
                        "distinction": "acquire through a deliberate process",
                        "example": "We obtained the logs from the backup bucket.",
                        "register": "formal",
                        "details": None,
                    },
                    {
                        "word": "fetch",
                        "distinction": "retrieve from a known place or API",
                        "example": "The worker fetches jobs from the queue.",
                        "register": "technical",
                        "details": None,
                    },
                    {
                        "word": "receive",
                        "distinction": "be given something that arrives",
                        "example": "We received the webhook within a second.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "good",
        "groups": [
            {
                "id": "good.quality",
                "pos": "ADJ",
                "sense_gloss": "of high or acceptable quality",
                "options": [
                    {
                        "word": "solid",
                        "distinction": "dependable and without obvious gaps",
                        "example": "The design is solid enough to ship this quarter.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "sound",
                        "distinction": "well reasoned or structurally correct",
                        "example": "That is a sound approach for the migration.",
                        "register": "formal",
                        "details": None,
                    },
                    {
                        "word": "reliable",
                        "distinction": "performs consistently over time",
                        "example": "The new job runner has been reliable for three weeks.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "hard",
        "groups": [
            {
                "id": "hard.difficulty",
                "pos": "ADJ",
                "sense_gloss": "difficult to do or understand",
                "options": [
                    {
                        "word": "difficult",
                        "distinction": "requires skill or effort to complete",
                        "example": "The upgrade path is difficult without downtime.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "demanding",
                        "distinction": "takes sustained effort or attention",
                        "example": "On-call this week has been demanding.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "tough",
                        "distinction": "challenging in a practical, informal sense",
                        "example": "Debugging the race condition was tough.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "absurd",
        "groups": [
            {
                "id": "idiom.absurd",
                "pos": "ADJ",
                "sense_gloss": "nightmarishly complex and senseless",
                "options": [
                    {
                        "word": "Kafkaesque",
                        "distinction": "nightmarishly complex, opaque, and helpless-feeling",
                        "example": "The appeal process was Kafkaesque: new forms for every reply.",
                        "register": "neutral",
                        "details": {
                            "meaning": "a bewildering bureaucratic nightmare with no clear exit",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "A Kafkaesque book club on Kafka's novels.",
                            "avoid_when": "when the process is complex but still clear and fair",
                            "origin": "From Franz Kafka's fiction, where characters "
                            "face endless opaque authority.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "advantage",
        "groups": [
            {
                "id": "idiom.advantage",
                "pos": "NOUN",
                "sense_gloss": "a controlling position in a contest",
                "options": [
                    {
                        "word": "upper hand",
                        "distinction": "the stronger position in a negotiation or conflict",
                        "example": "Having the only compatible vendor gave us the upper hand.",
                        "register": "neutral",
                        "details": {
                            "meaning": "control or advantage over the other side",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Raise your upper hand above your head.",
                            "avoid_when": "when both sides are equal and no leverage exists",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "agree",
        "groups": [
            {
                "id": "idiom.agree",
                "pos": "VERB",
                "sense_gloss": "share the same view or understanding",
                "options": [
                    {
                        "word": "on the same page",
                        "distinction": "everyone shares the same understanding of a plan or facts",
                        "example": "Let's get on the same page before the client call.",
                        "register": "neutral",
                        "details": {
                            "meaning": "share the same understanding of a situation or plan",
                            "tier": "everyday",
                            "region": "common",
                            "variants": ["get on the same page"],
                            "misuse_example": "We are on the same page of the document.",
                            "avoid_when": "when you mean you are literally looking at "
                            "the same document page",
                            "origin": None,
                        },
                    },
                    {
                        "word": "see eye to eye",
                        "distinction": "two people hold the same opinion, often after disagreement",
                        "example": "We finally see eye to eye on the launch date.",
                        "register": "neutral",
                        "details": {
                            "meaning": "hold the same opinion as someone else",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "I see eye to eye with the spreadsheet.",
                            "avoid_when": "when describing physical sight or a visual check",
                            "origin": None,
                        },
                    },
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "cautious",
        "groups": [
            {
                "id": "idiom.cautious",
                "pos": "VERB",
                "sense_gloss": "choose the safer option when unsure",
                "options": [
                    {
                        "word": "err on the side of caution",
                        "distinction": "prefer the safer choice when unsure",
                        "example": "We erred on the side of caution and delayed the cutover.",
                        "register": "neutral",
                        "details": {
                            "meaning": "choose safety over speed when the risk is unclear",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Use literal caution crossing ice; this "
                            "phrase is figurative.",
                            "avoid_when": "when delay itself creates more risk than acting",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "chance",
        "groups": [
            {
                "id": "idiom.chance",
                "pos": "NOUN",
                "sense_gloss": "a small likelihood of success",
                "options": [
                    {
                        "word": "a long shot",
                        "distinction": "unlikely to succeed but still worth trying",
                        "example": "Winning the RFP without a local partner is a long shot.",
                        "register": "neutral",
                        "details": {
                            "meaning": "an attempt with a low chance of success",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "We took a long shot of the skyline with the camera.",
                            "avoid_when": "when the odds are actually strong, or when "
                            "you mean a camera shot",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "choice",
        "groups": [
            {
                "id": "idiom.choice",
                "pos": "NOUN",
                "sense_gloss": "an offer with no real alternative",
                "options": [
                    {
                        "word": "Hobson's choice",
                        "distinction": "take the one option on offer or nothing",
                        "example": "Accept this vendor or cancel the project: a Hobson's choice.",
                        "register": "neutral",
                        "details": {
                            "meaning": "no real choice; only one option is available",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Hobson offered many horses but only the "
                            "one by the door.",
                            "avoid_when": "when several genuine alternatives exist",
                            "origin": "From Thomas Hobson, who hired out horses and "
                            "made riders take the next horse in line.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "clarify",
        "groups": [
            {
                "id": "idiom.clarify",
                "pos": "VERB",
                "sense_gloss": "remove tension or misunderstanding",
                "options": [
                    {
                        "word": "clear the air",
                        "distinction": "talk openly so tension or confusion ends",
                        "example": "We cleared the air after the missed handoff.",
                        "register": "neutral",
                        "details": {
                            "meaning": "resolve tension by discussing the issue openly",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Open a window to clear the air in the room.",
                            "avoid_when": "when the issue needs a written decision, not a talk",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "commitment",
        "groups": [
            {
                "id": "idiom.commitment",
                "pos": "VERB",
                "sense_gloss": "pass a point of no return",
                "options": [
                    {
                        "word": "cross the Rubicon",
                        "distinction": "take an irreversible step into conflict or change",
                        "example": "Deleting the dual-write path crosses the Rubicon on the "
                        "migration.",
                        "register": "neutral",
                        "details": {
                            "meaning": "commit to a course that cannot easily be undone",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Cross the Rubicon river on the hiking map.",
                            "avoid_when": "when the step is still easily reversible",
                            "origin": "Caesar crossed the Rubicon into Italy and made "
                            "civil war inevitable.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "compromise",
        "groups": [
            {
                "id": "idiom.compromise",
                "pos": "VERB",
                "sense_gloss": "settle differences by each side giving ground",
                "options": [
                    {
                        "word": "meet halfway",
                        "distinction": "each side gives up something to agree",
                        "example": "We met halfway on the timeline and the scope.",
                        "register": "neutral",
                        "details": {
                            "meaning": "reach agreement by mutual compromise",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Meet halfway between the two offices for coffee.",
                            "avoid_when": "when one side must not concede on a hard requirement",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "contact",
        "groups": [
            {
                "id": "idiom.contact",
                "pos": "VERB",
                "sense_gloss": "briefly check in with someone",
                "options": [
                    {
                        "word": "touch base",
                        "distinction": "have a short sync to share status or align",
                        "example": "Can we touch base tomorrow on the launch checklist?",
                        "register": "neutral",
                        "details": {
                            "meaning": "make brief contact to exchange updates",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Please touch base of the statue carefully.",
                            "avoid_when": "when you need a formal written decision, not "
                            "a quick sync",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "control",
        "groups": [
            {
                "id": "idiom.control",
                "pos": "ADJ",
                "sense_gloss": "oppressive surveillance and doublespeak",
                "options": [
                    {
                        "word": "Orwellian",
                        "distinction": "oppressive control through surveillance or twisted "
                        "language",
                        "example": "An Orwellian policy renamed layoffs as rightsizing without "
                        "data.",
                        "register": "neutral",
                        "details": {
                            "meaning": "authoritarian control that warps truth or privacy",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "An Orwellian reading group about George Orwell.",
                            "avoid_when": "when criticism is merely about strict but "
                            "transparent rules",
                            "origin": "From George Orwell's writing on totalitarian "
                            "language and surveillance.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "cut",
        "groups": [
            {
                "id": "idiom.cut",
                "pos": "VERB",
                "sense_gloss": "do a job in a careless or incomplete way to save time or cost",
                "options": [
                    {
                        "word": "cut corners",
                        "distinction": "skip steps or reduce quality to go faster or cheaper",
                        "example": "They cut corners on testing and shipped with known gaps.",
                        "register": "neutral",
                        "details": {
                            "meaning": "skip necessary steps to save time or money",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "We cut corners of the paper for the craft project.",
                            "avoid_when": "when you mean a literal cut, or when quality "
                            "and safety matter",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "deal",
        "groups": [
            {
                "id": "idiom.deal",
                "pos": "NOUN",
                "sense_gloss": "a bargain that sells your principles",
                "options": [
                    {
                        "word": "Faustian bargain",
                        "distinction": "a deal that gains short-term power at a moral cost",
                        "example": "Trading user privacy for growth metrics is a Faustian bargain.",
                        "register": "neutral",
                        "details": {
                            "meaning": "gain something valuable by giving up something essential",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "A Faustian bargain sale sticker on a novel.",
                            "avoid_when": "when the trade-off is modest and reversible",
                            "origin": "In the Faust legend, Faust sells his soul to the "
                            "devil for knowledge and power.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "delay",
        "groups": [
            {
                "id": "idiom.delay",
                "pos": "VERB",
                "sense_gloss": "push a hard decision into the future",
                "options": [
                    {
                        "word": "kick the can down the road",
                        "distinction": "postpone a hard decision without solving it",
                        "example": "We kicked the can down the road on the vendor lock-in.",
                        "register": "neutral",
                        "details": {
                            "meaning": "delay dealing with a problem instead of resolving it",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Kick the can down the road as a game.",
                            "avoid_when": "when a short, planned deferral with a clear "
                            "owner is fine",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "difficult",
        "groups": [
            {
                "id": "idiom.difficult",
                "pos": "NOUN",
                "sense_gloss": "a hard struggle toward a goal",
                "options": [
                    {
                        "word": "uphill battle",
                        "distinction": "a difficult effort against strong resistance",
                        "example": "Convincing finance without data will be an uphill battle.",
                        "register": "neutral",
                        "details": {
                            "meaning": "a struggle that faces strong obstacles",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "The hike was literally uphill in strong wind.",
                            "avoid_when": "when the path is actually clear and well supported",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "dilemma",
        "groups": [
            {
                "id": "idiom.dilemma",
                "pos": "NOUN",
                "sense_gloss": "a bind where every option blocks another",
                "options": [
                    {
                        "word": "Catch-22",
                        "distinction": "a rule that makes escape impossible by circular logic",
                        "example": "You need experience to get the role, but you need the role "
                        "to get experience: a Catch-22.",
                        "register": "neutral",
                        "details": {
                            "meaning": "a no-win situation created by contradictory rules",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Please catch 22 of the balls in the drill.",
                            "avoid_when": "when a hard choice still has a workable path",
                            "origin": "From Joseph Heller's novel, where airmen could "
                            "only be grounded for insanity but asking proved "
                            "they were sane.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "easy",
        "groups": [
            {
                "id": "idiom.easy",
                "pos": "NOUN",
                "sense_gloss": "the simplest gains available first",
                "options": [
                    {
                        "word": "low-hanging fruit",
                        "distinction": "easy improvements worth doing first",
                        "example": "Fixing the empty states is low-hanging fruit.",
                        "register": "neutral",
                        "details": {
                            "meaning": "tasks that give good results with little effort",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Pick the low-hanging fruit from the orchard.",
                            "avoid_when": "when the easy work hides a deeper required fix",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "effort",
        "groups": [
            {
                "id": "idiom.effort",
                "pos": "NOUN",
                "sense_gloss": "extra work beyond the minimum",
                "options": [
                    {
                        "word": "go the extra mile",
                        "distinction": "do more than is strictly required to help",
                        "example": "She went the extra mile and wrote a migration guide.",
                        "register": "neutral",
                        "details": {
                            "meaning": "put in more effort than expected to get a better result",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "We will go the extra mile on the highway.",
                            "avoid_when": "in formal contracts where only defined scope matters",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "estimate",
        "groups": [
            {
                "id": "idiom.estimate",
                "pos": "NOUN",
                "sense_gloss": "a rough number without precision",
                "options": [
                    {
                        "word": "ballpark",
                        "distinction": "an approximate figure good enough for planning",
                        "example": "Give me a ballpark for the migration effort.",
                        "register": "neutral",
                        "details": {
                            "meaning": "a rough estimate, not an exact number",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Meet me at the ballpark after work.",
                            "avoid_when": "when finance or legal needs an exact figure",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "finish",
        "groups": [
            {
                "id": "idiom.finish",
                "pos": "VERB",
                "sense_gloss": "bring something to a close",
                "options": [
                    {
                        "word": "wrap up",
                        "distinction": "finish the remaining small parts of a task or meeting",
                        "example": "Let's wrap up the open questions before noon.",
                        "register": "neutral",
                        "details": {
                            "meaning": "bring the last bits of work or a meeting to a close",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Please wrap up the gift with ribbon.",
                            "avoid_when": "when you mean packaging something, or when "
                            "work is only paused",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "force",
        "groups": [
            {
                "id": "idiom.force",
                "pos": "ADJ",
                "sense_gloss": "forcing everything into one rigid shape",
                "options": [
                    {
                        "word": "Procrustean",
                        "distinction": "forcing different cases into one rigid mould",
                        "example": "A Procrustean policy treated every bug as a sev-1.",
                        "register": "neutral",
                        "details": {
                            "meaning": "enforcing uniformity by cutting or stretching "
                            "what does not fit",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "A Procrustean bed in the museum exhibit.",
                            "avoid_when": "when a single clear standard truly fits all cases",
                            "origin": "Procrustes made travellers fit his bed by "
                            "stretching or cutting them.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "futile",
        "groups": [
            {
                "id": "idiom.futile",
                "pos": "VERB",
                "sense_gloss": "fight imaginary or unwinnable foes",
                "options": [
                    {
                        "word": "tilt at windmills",
                        "distinction": "attack imaginary enemies or unwinnable causes",
                        "example": "Arguing with every drive-by comment is tilting at windmills.",
                        "register": "neutral",
                        "details": {
                            "meaning": "waste effort fighting the wrong or impossible opponent",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Tilt at windmills on the Dutch hillside "
                            "for a photo.",
                            "avoid_when": "when the fight is necessary and winnable",
                            "origin": "Don Quixote attacked windmills thinking they were giants.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "greed",
        "groups": [
            {
                "id": "idiom.greed",
                "pos": "NOUN",
                "sense_gloss": "success that turns everything to profit",
                "options": [
                    {
                        "word": "Midas touch",
                        "distinction": "a gift for making everything profitable, sometimes too "
                        "much",
                        "example": "Her Midas touch turned every side project into revenue.",
                        "register": "neutral",
                        "details": {
                            "meaning": "an ability to make ventures succeed financially",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "The Midas touch exhibit about King Midas.",
                            "avoid_when": "when luck, not skill, explains the wins",
                            "origin": "King Midas wished that all he touched would turn "
                            "to gold, then could not eat.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "guideline",
        "groups": [
            {
                "id": "idiom.guideline",
                "pos": "NOUN",
                "sense_gloss": "a practical rule based on experience",
                "options": [
                    {
                        "word": "rule of thumb",
                        "distinction": "a simple practical guideline, not an exact law",
                        "example": "As a rule of thumb, keep PRs under four hundred lines.",
                        "register": "neutral",
                        "details": {
                            "meaning": "an approximate principle that usually works",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Measure with the length of your thumb.",
                            "avoid_when": "when a precise standard or regulation applies",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "ignore",
        "groups": [
            {
                "id": "idiom.ignore",
                "pos": "VERB",
                "sense_gloss": "deliberately overlook a fault",
                "options": [
                    {
                        "word": "turn a blind eye",
                        "distinction": "choose not to notice something wrong",
                        "example": "Leadership turned a blind eye to the skipped reviews.",
                        "register": "neutral",
                        "details": {
                            "meaning": "deliberately ignore a problem or rule breach",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Turn a blind eye toward the bright light.",
                            "avoid_when": "when you must report or stop the issue",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "join",
        "groups": [
            {
                "id": "idiom.join",
                "pos": "VERB",
                "sense_gloss": "decide to support a plan",
                "options": [
                    {
                        "word": "jump on board",
                        "distinction": "agree to join a plan or effort",
                        "example": "Once legal jumped on board, we booked the launch.",
                        "register": "neutral",
                        "details": {
                            "meaning": "commit to supporting a proposal",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Jump on board the train before it leaves.",
                            "avoid_when": "when a formal signed approval is required",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "learn",
        "groups": [
            {
                "id": "idiom.learn",
                "pos": "VERB",
                "sense_gloss": "catch up on needed context",
                "options": [
                    {
                        "word": "get up to speed",
                        "distinction": "learn enough context to contribute",
                        "example": "I need a day to get up to speed on the billing code.",
                        "register": "neutral",
                        "details": {
                            "meaning": "learn the current state so you can work effectively",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Get up to speed on the treadmill.",
                            "avoid_when": "when the person already knows the domain well",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "limit",
        "groups": [
            {
                "id": "idiom.limit",
                "pos": "VERB",
                "sense_gloss": "set a firm boundary on what is acceptable",
                "options": [
                    {
                        "word": "draw the line",
                        "distinction": "state what you will not accept",
                        "example": "We draw the line at shipping without a rollback plan.",
                        "register": "neutral",
                        "details": {
                            "meaning": "set a clear limit on acceptable behaviour or risk",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Draw the line with a ruler on the page.",
                            "avoid_when": "when you are still open to negotiation on that point",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "postpone",
        "groups": [
            {
                "id": "idiom.postpone",
                "pos": "VERB",
                "sense_gloss": "delay something that is not urgent now",
                "options": [
                    {
                        "word": "put on the back burner",
                        "distinction": "delay work that matters less right now",
                        "example": "We put the redesign on the back burner until after launch.",
                        "register": "neutral",
                        "details": {
                            "meaning": "set aside for later because other work has priority",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Put the kettle on the back burner of the stove.",
                            "avoid_when": "when delay would break a commitment or cause harm",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "pressure",
        "groups": [
            {
                "id": "idiom.pressure",
                "pos": "ADJ",
                "sense_gloss": "facing tight deadlines or scrutiny",
                "options": [
                    {
                        "word": "under the gun",
                        "distinction": "forced to deliver under heavy time pressure",
                        "example": "The team is under the gun to ship before the freeze.",
                        "register": "neutral",
                        "details": {
                            "meaning": "working with little time left and high stakes",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "The prop was under the gun on the film set.",
                            "avoid_when": "in calm planning discussions where pressure "
                            "is not the point",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "problem",
        "groups": [
            {
                "id": "idiom.problem",
                "pos": "NOUN",
                "sense_gloss": "an obvious issue nobody wants to name",
                "options": [
                    {
                        "word": "elephant in the room",
                        "distinction": "a major issue everyone avoids discussing",
                        "example": "The elephant in the room was the missing on-call rotation.",
                        "register": "neutral",
                        "details": {
                            "meaning": "an obvious problem that people are not talking about",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "There is an elephant in the room at the "
                            "zoo exhibit.",
                            "avoid_when": "when the issue is already on the agenda and "
                            "being handled",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "progress",
        "groups": [
            {
                "id": "idiom.progress",
                "pos": "VERB",
                "sense_gloss": "make a measurable improvement",
                "options": [
                    {
                        "word": "move the needle",
                        "distinction": "change a metric enough to notice",
                        "example": "The new onboarding flow finally moved the needle on "
                        "activation.",
                        "register": "neutral",
                        "details": {
                            "meaning": "produce a noticeable change in an important measure",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Please move the needle on the dial to the left.",
                            "avoid_when": "when the change is tiny or the metric is the wrong one",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "recovery",
        "groups": [
            {
                "id": "idiom.recovery",
                "pos": "VERB",
                "sense_gloss": "recover strongly after ruin",
                "options": [
                    {
                        "word": "rise from the ashes",
                        "distinction": "recover strongly after a collapse",
                        "example": "The team rose from the ashes after the outage with a new "
                        "runbook.",
                        "register": "neutral",
                        "details": {
                            "meaning": "rebuild successfully after a serious failure",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Rise from the ashes of the campfire in a "
                            "literal sense.",
                            "avoid_when": "when recovery has not yet begun",
                            "origin": "The phoenix of myth burned and was reborn from "
                            "its own ashes.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "reject",
        "groups": [
            {
                "id": "idiom.reject",
                "pos": "VERB",
                "sense_gloss": "dismiss an idea firmly",
                "options": [
                    {
                        "word": "shoot down",
                        "distinction": "reject a proposal quickly and firmly",
                        "example": "Legal shot down the third-party clause.",
                        "register": "neutral",
                        "details": {
                            "meaning": "dismiss an idea as unworkable",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Shoot down the clay targets at the range.",
                            "avoid_when": "when you only want light feedback, not a hard no",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "reveal",
        "groups": [
            {
                "id": "idiom.reveal",
                "pos": "VERB",
                "sense_gloss": "disclose a secret by accident or carelessness",
                "options": [
                    {
                        "word": "let the cat out of the bag",
                        "distinction": "reveal something that was meant to stay secret",
                        "example": "The memo let the cat out of the bag about the reorg.",
                        "register": "neutral",
                        "details": {
                            "meaning": "disclose a secret earlier than planned",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Let the cat out of the bag so it can walk.",
                            "avoid_when": "when the news was meant to be public already",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "risk",
        "groups": [
            {
                "id": "idiom.risk",
                "pos": "NOUN",
                "sense_gloss": "an action that releases many new troubles",
                "options": [
                    {
                        "word": "open Pandora's box",
                        "distinction": "start something that releases many unforeseen problems",
                        "example": "Rewriting the auth stack mid-quarter would open Pandora's box.",
                        "register": "neutral",
                        "details": {
                            "meaning": "begin a course of action that unleashes many new troubles",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Open Pandora's box on the shelf for the prop check.",
                            "avoid_when": "when the change is small and well contained",
                            "origin": "In Greek myth Pandora opened a jar and released "
                            "evils into the world.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "solution",
        "groups": [
            {
                "id": "idiom.solution",
                "pos": "VERB",
                "sense_gloss": "solve a hard problem with a bold cut",
                "options": [
                    {
                        "word": "cut the Gordian knot",
                        "distinction": "solve a tangled problem with a decisive bold move",
                        "example": "They cut the Gordian knot by sunsetting the legacy API.",
                        "register": "neutral",
                        "details": {
                            "meaning": "end a complex tangle by decisive action rather "
                            "than patient unpicking",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Cut the Gordian knot of rope for craft class.",
                            "avoid_when": "when careful stepwise untangling is safer",
                            "origin": "Alexander the Great, facing an impossible knot, "
                            "cut it with his sword.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "start",
        "groups": [
            {
                "id": "idiom.start",
                "pos": "VERB",
                "sense_gloss": "begin work or a process",
                "options": [
                    {
                        "word": "get the ball rolling",
                        "distinction": "start a process so others can continue",
                        "example": "I'll get the ball rolling with a draft agenda.",
                        "register": "neutral",
                        "details": {
                            "meaning": "begin something so momentum builds",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Get the ball rolling across the floor.",
                            "avoid_when": "when a formal kickoff or signed start is required",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "strain",
        "groups": [
            {
                "id": "idiom.strain",
                "pos": "ADJ",
                "sense_gloss": "requiring enormous strength",
                "options": [
                    {
                        "word": "Herculean",
                        "distinction": "requiring extraordinary effort or strength",
                        "example": "Cleaning the legacy backlog was a Herculean effort.",
                        "register": "neutral",
                        "details": {
                            "meaning": "extremely demanding in labour or courage",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "A Herculean statue in the lobby.",
                            "avoid_when": "when the work is ordinary effort",
                            "origin": "Named for Hercules and his twelve labours of "
                            "immense difficulty.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "support",
        "groups": [
            {
                "id": "idiom.support",
                "pos": "VERB",
                "sense_gloss": "defend or help someone in a dispute",
                "options": [
                    {
                        "word": "go to bat for",
                        "distinction": "actively support someone when it counts",
                        "example": "She went to bat for the intern in the calibration meeting.",
                        "register": "neutral",
                        "details": {
                            "meaning": "speak up or act to defend someone's interests",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Go to bat for the home team in the stadium.",
                            "avoid_when": "when neutral facilitation is required "
                            "instead of advocacy",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "task",
        "groups": [
            {
                "id": "idiom.task",
                "pos": "NOUN",
                "sense_gloss": "endless labour that never finishes",
                "options": [
                    {
                        "word": "Sisyphean task",
                        "distinction": "endless work that resets before it finishes",
                        "example": "Manual spreadsheet syncs every morning are a Sisyphean task.",
                        "register": "neutral",
                        "details": {
                            "meaning": "labour that must be repeated forever without "
                            "lasting result",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Calling any long meeting Sisyphean "
                            "without the reset pattern.",
                            "avoid_when": "when the work has a clear end state",
                            "origin": "Sisyphus was condemned to roll a boulder uphill "
                            "only to watch it fall forever.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "temptation",
        "groups": [
            {
                "id": "idiom.temptation",
                "pos": "NOUN",
                "sense_gloss": "a lure that leads to downfall",
                "options": [
                    {
                        "word": "siren song",
                        "distinction": "an alluring call that leads people into danger",
                        "example": "The siren song of vanity metrics pulled the roadmap off "
                        "course.",
                        "register": "neutral",
                        "details": {
                            "meaning": "a tempting offer that hides serious harm",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "A siren song track on the playlist.",
                            "avoid_when": "when the opportunity is genuinely safe and valuable",
                            "origin": "In myth, sirens sang so sweetly that sailors "
                            "steered onto the rocks.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "threat",
        "groups": [
            {
                "id": "idiom.threat",
                "pos": "NOUN",
                "sense_gloss": "constant danger hanging overhead",
                "options": [
                    {
                        "word": "sword of Damocles",
                        "distinction": "a constant threat hanging over someone who seems secure",
                        "example": "The unpaid invoice hung over the renewal like a sword of "
                        "Damocles.",
                        "register": "neutral",
                        "details": {
                            "meaning": "imminent danger that makes a privileged "
                            "position precarious",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "A stage prop sword of Damocles hung from "
                            "the ceiling.",
                            "avoid_when": "when there is no real pending threat",
                            "origin": "Damocles sat under a sword hung by a hair to "
                            "learn how fragile power feels.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "trap",
        "groups": [
            {
                "id": "idiom.trap",
                "pos": "NOUN",
                "sense_gloss": "a gift that hides a threat",
                "options": [
                    {
                        "word": "Trojan horse",
                        "distinction": "something welcomed that secretly causes harm",
                        "example": "The free plugin was a Trojan horse for data exfiltration.",
                        "register": "neutral",
                        "details": {
                            "meaning": "an apparent benefit that conceals a damaging payload",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "A wooden Trojan horse prop for the school play.",
                            "avoid_when": "when the gift is inspected and truly safe",
                            "origin": "Greeks hid soldiers in a wooden horse that Troy "
                            "pulled inside its walls.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "unexpected",
        "groups": [
            {
                "id": "idiom.unexpected",
                "pos": "ADJ",
                "sense_gloss": "surprising and hard to predict",
                "options": [
                    {
                        "word": "out of left field",
                        "distinction": "sudden and unrelated to what came before",
                        "example": "The pricing change came out of left field in the Q&A.",
                        "register": "neutral",
                        "details": {
                            "meaning": "unexpected and seeming to come from nowhere",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "The throw came out of left field to home plate.",
                            "avoid_when": "when the event was clearly foreshadowed",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "unfinished",
        "groups": [
            {
                "id": "idiom.unfinished",
                "pos": "NOUN",
                "sense_gloss": "work that is still changing",
                "options": [
                    {
                        "word": "work in progress",
                        "distinction": "not finished; still being improved",
                        "example": "The dashboard is a work in progress this sprint.",
                        "register": "neutral",
                        "details": {
                            "meaning": "something incomplete that should not be judged as final",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "The art show titled Work in Progress opens Friday.",
                            "avoid_when": "when stakeholders need a finished deliverable now",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "victory",
        "groups": [
            {
                "id": "idiom.victory",
                "pos": "NOUN",
                "sense_gloss": "a win that costs too much",
                "options": [
                    {
                        "word": "Pyrrhic victory",
                        "distinction": "a win whose cost outweighs the gain",
                        "example": "Beating the deadline with three people burned out was a "
                        "Pyrrhic victory.",
                        "register": "neutral",
                        "details": {
                            "meaning": "success that leaves you worse off overall",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "They called any close match a Pyrrhic "
                            "victory without looking at costs.",
                            "avoid_when": "when the win was cheap and lasting",
                            "origin": "Named after King Pyrrhus, whose costly wins "
                            "against Rome nearly ruined his army.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "warning",
        "groups": [
            {
                "id": "idiom.warning",
                "pos": "NOUN",
                "sense_gloss": "a true warning that is ignored",
                "options": [
                    {
                        "word": "Cassandra",
                        "distinction": "a warning that is true but not believed",
                        "example": "Her Cassandra note about cache stampedes went unread.",
                        "register": "neutral",
                        "details": {
                            "meaning": "accurate foresight that others refuse to trust",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Cassandra is also a common given name.",
                            "avoid_when": "when the warning was vague or wrong",
                            "origin": "Cassandra of Troy was cursed to prophesy truth "
                            "that nobody believed.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "waste",
        "groups": [
            {
                "id": "idiom.waste",
                "pos": "VERB",
                "sense_gloss": "spend effort without getting results",
                "options": [
                    {
                        "word": "spinning wheels",
                        "distinction": "working hard without making progress",
                        "example": "Without the API key we were just spinning wheels.",
                        "register": "neutral",
                        "details": {
                            "meaning": "expending effort that does not advance the goal",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "The car was spinning wheels on the ice.",
                            "avoid_when": "when slow progress is still real progress",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "watch",
        "groups": [
            {
                "id": "idiom.watch",
                "pos": "VERB",
                "sense_gloss": "monitor something carefully",
                "options": [
                    {
                        "word": "keep an eye on",
                        "distinction": "watch something so problems are noticed early",
                        "example": "Keep an eye on error rates after the deploy.",
                        "register": "neutral",
                        "details": {
                            "meaning": "monitor carefully for changes or problems",
                            "tier": "everyday",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "Keep an eye on the table while I step out.",
                            "avoid_when": "when you need automated alerts, not human "
                            "attention alone",
                            "origin": None,
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "idiom",
        "head_lemma": "weakness",
        "groups": [
            {
                "id": "idiom.weakness",
                "pos": "NOUN",
                "sense_gloss": "a single vulnerable point",
                "options": [
                    {
                        "word": "Achilles' heel",
                        "distinction": "a critical weakness in an otherwise strong position",
                        "example": "Single-region hosting is our Achilles' heel.",
                        "register": "neutral",
                        "details": {
                            "meaning": "one serious vulnerability despite general strength",
                            "tier": "literary",
                            "region": "common",
                            "variants": [],
                            "misuse_example": "The statue showed Achilles' heel in marble.",
                            "avoid_when": "when many equal weaknesses exist, not one key flaw",
                            "origin": "In myth, Achilles was invulnerable except for "
                            "the heel that stayed dry when he was dipped in "
                            "the Styx.",
                        },
                    }
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "make",
        "groups": [
            {
                "id": "make.create",
                "pos": "VERB",
                "sense_gloss": "bring something into existence",
                "options": [
                    {
                        "word": "create",
                        "distinction": "bring into being as a new entity",
                        "example": "Create a branch before changing the schema.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "produce",
                        "distinction": "generate as output of a process",
                        "example": "The pipeline produces a daily report.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "assemble",
                        "distinction": "put parts together into a whole",
                        "example": "We assembled the release notes from the PRs.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "problem",
        "groups": [
            {
                "id": "problem.issue",
                "pos": "NOUN",
                "sense_gloss": "something wrong that needs attention",
                "options": [
                    {
                        "word": "issue",
                        "distinction": "a concrete matter to track or fix",
                        "example": "The main issue is the missing index.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "obstacle",
                        "distinction": "something blocking progress toward a goal",
                        "example": "Legal review is the only obstacle left.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "setback",
                        "distinction": "a delay or reverse after progress",
                        "example": "The outage was a setback for the launch.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
    {
        "kind": "precision",
        "head_lemma": "thing",
        "groups": [
            {
                "id": "thing.object",
                "pos": "NOUN",
                "sense_gloss": "a vague stand-in for an object, idea, or matter",
                "options": [
                    {
                        "word": "item",
                        "distinction": "one discrete entry in a list or backlog",
                        "example": "Move that item to the next sprint.",
                        "register": "neutral",
                        "details": None,
                    },
                    {
                        "word": "matter",
                        "distinction": "a subject under discussion or decision",
                        "example": "Security is a separate matter from latency.",
                        "register": "formal",
                        "details": None,
                    },
                    {
                        "word": "element",
                        "distinction": "one part of a larger system or design",
                        "example": "Caching is a key element of the plan.",
                        "register": "neutral",
                        "details": None,
                    },
                ],
            }
        ],
    },
]
