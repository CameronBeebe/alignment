"""Versioned search rules. Patterns operate on case-folded text with hyphens replaced by spaces."""

import re
import unicodedata


def norm(text):
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[-‐‑‒–—_/]", " ", unicodedata.normalize("NFKC", text).lower()),
    )


def rx(pattern):
    return re.compile(r"\b(?:" + pattern + r")\b")


AI = rx(
    r"llms?|vlms?|mlms?|(?:language|foundation|generative|diffusion|vision language|frontier|multimodal) models?|reinforcement learning|machine learning|robot(?:s|ic|ics)?|autonomous (?:agents?|systems?|vehicles?)|artificial intelligence|neural (?:networks?|polic(?:y|ies)|controllers?)|deep learning|chatbots?|ai|agentic|learning based|learned polic(?:y|ies)|learning enabled|intelligent agents?"
)
GEN = rx(
    r"llms?|vlms?|(?:language|foundation|generative|diffusion|vision language|frontier|multimodal) models?|chatbots?|agentic|artificial general intelligence"
)
NAMED = rx(
    r"(?:ai|agent|agentic|llm|model|safety|preference|value|behavioral|behavioural|goal|intent|language model|large language model) alignment|alignment (?:of|for|in|with) (?:large language|llms?|human (?:values?|intent(?:ions?)?|preferences?)|ai systems?|language models?)|align(?:ing|ed|ment)? .{0,55}?(?:human (?:preferences?|values?|intent(?:ions?)?)|user (?:preferences?|intent(?:ions?)?))|aligning (?:large )?language models?|misaligned (?:ai|agents?|models?)"
)
NEUTRAL = rx(
    r"(?:ai|llm|agent|agentic|language model|model|artificial intelligence) safety|safety (?:of|in|for) (?:autonomous agents?|ai|llms?|(?:large )?language models?|foundation models?)|harmlessness|corrigibilit(?:y|ies)|scalable oversight|reward hacking|specification gaming|goal misgeneralization|deceptive alignment|power seeking|mechanistic interpretability|value learning|human oversight|jailbreak(?:ing|s)?|prompt injections?|sycophan(?:cy|tic)|ai governance|existential risk|unsafe (?:actions?|content|responses?|behaviou?rs?|outputs?)|safety (?:policy|policies|constraints?|guarantees?)|human (?:values|preferences|intentions)|toxic (?:output|language|content|generation)|truthful(?:ness|qa)|instruction following"
)
WEIGHT = rx(
    r"rlhf|rlaif|dpo|direct preference optimi[sz]ation|(?:preference|policy|reward) optimi[sz]ation|(?:reinforcement learning|learning) from (?:human|ai) feedback|instruction tun(?:ing|ed)|(?:supervised|safety|alignment|adversarial) fine ?tun(?:ing|ed)|(?:preference|safety|alignment|adversarial) train(?:ing|ed)|constitutional ai|reward model(?:ling|ing|s)?|model editing|weight editing|parameter efficient fine tuning|unlearning|fine ?tun(?:e|ed|ing)|post train(?:ing|ed)"
)
WD = rx(
    r"rlhf|rlaif|direct preference optimi[sz]ation|(?:reinforcement learning|learning) from (?:human|ai) feedback|constitutional ai|(?:preference|alignment|safety) (?:train(?:ing|ed)|fine tun(?:ing|ed))|preference optimi[sz]ation"
)
EXTERNAL = rx(
    r"guard ?rails?|guard models?|runtime (?:monitor(?:s|ing)?|enforcement|assurance|verification|safety|shield(?:s|ing)?)|run time (?:monitoring|assurance|enforcement|verification)|safety (?:shield(?:ing|s)?|filters?|layers?|harness(?:es)?|monitors?)|shield(?:s|ing|ed)?|action mask(?:s|ing)?|(?:control|neural) barrier (?:functions?|certificates?)|model predictive (?:safety|shielding)|reference monitors?|(?:un)?trusted (?:monitoring|editing)|ai control|control protocols?|(?:agent|safety) harness(?:es)?|(?:tool|action) (?:polic(?:y|ies)|permissions?|authorization|gating|validation)|capability based|least privilege|access control|information flow control|policy enforcement|enforc(?:e|ing|ement of) (?:safety|security) polic(?:y|ies)|sandbox(?:ing|es|ed)?|human (?:approval|intervention)|formal (?:shields?|safety guarantees)|constrained decoding|grammar (?:guided|constrained) decoding|json schema|structured (?:generation|outputs?)|systems? theoretic(?:al)?|control theoretic(?:al)?|control theory|stpa|feedback control|closed loop control|supervisory control"
)
ED = rx(
    r"guard ?rails?|runtime (?:monitoring|assurance|enforcement|verification)|run time (?:monitoring|assurance|enforcement|verification)|safety (?:harness(?:es)?|filters?|shield(?:ing|s)?|monitors?)|shielding|control barrier functions?|ai control|trusted (?:monitoring|editing)|(?:agent|safety) harness(?:es)?|tool permissions?|information flow control|policy enforcement|grammar constrained decoding|constrained decoding|json schema|systems? theoretic process analysis"
)
INFERENCE = rx(
    r"(?:inference|test|decoding) time (?:align(?:ment)?|steer(?:ing)?|safety|control|guidance|intervention)|activation (?:steering|addition|engineering)|steering vectors?|representation engineering|safety decoding|safe decoding|(?:reward|classifier|contrastive) guided decoding|best of n|rejection sampling|rerank(?:ing|ers?)|system prompts?|(?:prompt|in context) (?:steering|alignment)|self (?:critique|refinement|correction)|training free alignment"
)
TECH = rx(
    r"safe reinforcement learning|constrained (?:markov decision processes?|reinforcement learning)|learning (?:safe|safety) (?:policies|controllers)|safe exploration|certified (?:safety|controllers)|safety critical (?:learning|control)|safe learning based control"
)
# FTS5 union is a low-cost superset of the main search entry points. Keep it in sync with new rules.
PRE = """align* OR misalign* OR safe* OR guard* OR shield* OR "barrier function" OR "barrier functions" OR "barrier certificate" OR "barrier certificates" OR runtime OR "run time" OR "human feedback" OR "ai feedback" OR rlhf OR rlaif OR preference* OR "constitutional ai" OR oversight OR corrigib* OR harmless* OR "reward hacking" OR "specification gaming" OR "goal misgeneralization" OR "power seeking" OR "mechanistic interpretability" OR "value learning" OR jailbreak* OR "prompt injection" OR "prompt injections" OR sycophan* OR governance OR "existential risk" OR unsafe OR "human values" OR "human intentions" OR toxic OR truthful* OR "instruction following" OR "ai control" OR "trusted monitoring" OR "trusted editing" OR harness* OR "tool permissions" OR "information flow control" OR "policy enforcement" OR "constrained decoding" OR "json schema" OR "process analysis" OR "safe exploration" OR "constrained reinforcement" OR "constrained markov" OR steering OR "representation engineering" OR "system prompt" OR "system prompts" OR "rejection sampling" OR rerank* OR "best of" OR "self correction" OR "self critique" OR "self refinement" OR "guided decoding" OR "activation addition" OR "training free" OR "test time" OR "inference time" OR "decoding time" """
PRE += ' OR "control theory" OR "control theoretic" OR "systems theoretic" OR "system theoretic" OR stpa OR "feedback control" OR "closed loop control" OR "supervisory control" OR sandbox* OR "access control" OR "least privilege" OR "capability based" OR "structured generation" OR "structured outputs" OR "structured output" OR "action masking" OR "human approval" OR "human intervention" OR "tool policy" OR "tool policies" OR "control protocols" OR "reference monitor" OR "reference monitors" OR "tool authorization" OR "action validation" OR "tool validation" OR "tool gating" OR "tool permission" OR "action policy" OR "action policies" OR "action permissions" OR "action authorization" OR "action gating" OR "formal shields" OR "control protocol" OR "grammar guided decoding" OR "security policies"'
METRICS = {
    "preference / win rate": r"win rates?|human preference (?:score|rate)|pairwise (?:win|preference)|alpacaeval|arena hard",
    "harm / attack success": r"attack success (?:rate|ratio)|asr|harmbench|strongreject|jailbreakbench",
    "refusal / over-refusal": r"(?:over ?refusal|false refusals?|refusal rates?|xstest)",
    "safety / constraint violations": r"constraint violations?|safety violations?|violation rates?|unsafe (?:action|response) rates?",
    "task / utility": r"task (?:success|completion|accuracy)|benign utility|utility loss|pass@\d+",
    "truthfulness / hallucination": r"truthfulqa|hallucination rates?|factual consistency",
    "operating cost": r"latency|false positive rates?|false alarm rates?|audit budgets?|intervention rates?",
}
METRICS = {k: rx(v) for k, v in METRICS.items()}
FACETS = {
    k: rx(v)
    for k, v in {
        "systems/control theory": r"systems? theor(?:y|etic(?:al)?)|control theor(?:y|etic(?:al)?)|stpa|cybernetics|feedback control|closed loop control|supervisory control",
        "formal safety": r"control barrier functions?|shield(?:ing|s)?|runtime assurance|temporal logic|safety filters?|reachability analysis",
        "schemas/tools/harnesses": r"json schemas?|(?:constrained|grammar guided) decoding|reference monitors?|tool (?:polic(?:y|ies)|permissions?|gating)|agent harness(?:es)?|safety harness(?:es)?|information flow control|policy enforcement|least privilege",
        "oversight/monitoring": r"scalable oversight|(?:un)?trusted (?:monitoring|editing)|guardrails?|runtime monitoring|guard models?|human oversight",
        "evaluation": r"benchmarks?|evaluat(?:e|ion|ing)|red teaming",
        "governance/values": r"governance|value pluralism|collective alignment|human values|deliberative alignment",
    }.items()
}


def screen(title, abstract):
    t = norm(title + ". " + abstract)
    named, neutral = bool(NAMED.search(t)), bool(NEUTRAL.search(t))
    ai = bool(AI.search(t))
    gen = bool(GEN.search(t))
    lanes = []
    if ai and named:
        lanes.append("named")
    if ai and neutral:
        lanes.append("goal")
    if ai and WD.search(t):
        lanes.append("training")
    if ai and ED.search(t):
        lanes.append("system")
    if (
        ai
        and INFERENCE.search(t)
        and (named or neutral or "safety" in t or "align" in t)
    ):
        lanes.append("steering")
    if (
        ai
        and (gen or re.search(r"\b(?:risk|safe|unsafe|hazard|security|assurance)", t))
        and EXTERNAL.search(t)
    ):
        lanes.append("control_expansion")
    if TECH.search(t):
        lanes.append("safe_learning")
    return lanes


def measure(title, abstract):
    t = norm(title + ". " + abstract)
    w, e, i = [p.search(t) for p in (WEIGHT, EXTERNAL, INFERENCE)]
    group = (
        "mixed"
        if w and (e or i)
        else "weights" if w else "external" if e else "inference" if i else "unresolved"
    )
    return dict(
        auto_group=group,
        named=bool(NAMED.search(t)),
        generative=bool(GEN.search(t)),
        weight_hit=w[0] if w else "",
        external_hit=e[0] if e else "",
        inference_hit=i[0] if i else "",
        facets=[k for k, p in FACETS.items() if p.search(t)],
        metrics=[k for k, p in METRICS.items() if p.search(t)],
    )
