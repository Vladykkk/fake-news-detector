"""Constants for the IPSO analysis pipeline."""

# Rhetorical manipulation patterns (regex-based, applied on English-translated text)
RHETORIC_PATTERNS_EN = {
    'whataboutism': [
        r'\bwhat about\b',
        r'\band what about\b',
        r'\bbut what about\b',
        r'\bwhere were you when\b',
        r'\bwhy don.t you talk about\b',
    ],
    'false_authority': [
        r'\bsources in\b',
        r'\bexperts say\b',
        r'\banalysts claim\b',
        r'\binsiders report\b',
        r'\baccording to military sources\b',
        r'\bofficial sources confirm\b',
    ],
    'fear_panic': [
        r'\bmillions will die\b',
        r'\bcollapse is inevitable\b',
        r'\bno hope\b',
        r'\ball is lost\b',
        r'\bwithin days\b.{0,20}\bfall\b',
        r'\bno chance of\b',
    ],
    'demoralization': [
        r'\buseless resistance\b',
        r'\bfutile to fight\b',
        r'\bzelensky.{0,20}fled\b',
        r'\bzelensky.{0,20}billion\b',
        r'\bcoward\b',
        r'\bsurrender.{0,30}only option\b',
    ],
    'false_equivalence': [
        r'\bboth sides\b',
        r'\bequally guilty\b',
        r'\bboth are wrong\b',
        r'\bno difference between\b',
        r'\bsame as\b.{0,30}\bnazi\b',
    ],
    'cherry_picking': [
        r'\bone soldier said\b',
        r'\bone case proves\b',
        r'\bas an example\b.{0,20}\bthis shows all\b',
    ],
}

# Ukrainian rhetorical manipulation patterns (applied on original Ukrainian text)
RHETORIC_PATTERNS_UK = {
    'whataboutism': [
        r'\bа що щодо\b',
        r'\bа як щодо\b',
        r'\bа де ви були\b',
        r'\bа що ваш[іа]\b',
        r'\bчому ви мовчите про\b',
        r'\bподивіться краще на себе\b',
    ],
    'false_authority': [
        r'\bджерела повідомляють\b',
        r'\bексперти кажуть\b',
        r'\bаналітики стверджують\b',
        r'\bза даними джерел\b',
        r'\bза інформацією\b',
        r'\bінсайдери\b',
        r'\bвоєнні джерела\b',
    ],
    'fear_panic': [
        r'\bмільйони загинуть\b',
        r'\bкатастроф[аи]\b',
        r'\bнемає надії\b',
        r'\bвсе пропало\b',
        r'\bнемає шансів\b',
        r'\bколапс\b',
        r'\bкрах\b',
        r'\bнас чекає\b.{0,20}\bзагибель\b',
        r'\bапокаліпсис\b',
    ],
    'demoralization': [
        r'\bопір безнадійний\b',
        r'\bмарн[оіа] воювати\b',
        r'\bзеленськ.{0,20}втік\b',
        r'\bзеленськ.{0,20}мільярд\b',
        r'\bздаватися\b.{0,20}\bєдин\b',
        r'\bзрад[аиив]\b',
        r'\bнікому ви не потрібні\b',
        r'\bбезглуздий опір\b',
    ],
    'false_equivalence': [
        r'\bобидві сторони\b',
        r'\bоднаково винн[іи]\b',
        r'\bобидва не прав[іи]\b',
        r'\bнемає різниці між\b',
        r'\bтак само як\b.{0,20}\bнацис\b',
        r'\bвсі однакові\b',
    ],
    'cherry_picking': [
        r'\bодин солдат сказав\b',
        r'\bодин випадок доводить\b',
        r'\bось приклад\b.{0,15}\bвсі\b',
        r'\bось бачите\b',
    ],
}


def get_rhetoric_patterns(language: str = 'en') -> dict:
    """Return rhetoric patterns for the given language."""
    if language == 'uk':
        return RHETORIC_PATTERNS_UK
    return RHETORIC_PATTERNS_EN


# Combined patterns (for backward compatibility)
RHETORIC_PATTERNS = RHETORIC_PATTERNS_EN

# Narrative labels for LLM classification
NARRATIVE_LABELS = [
    'demoralization',
    'distrust_institutions',
    'false_equivalence',
    'panic_fear',
    'military_losses_exaggeration',
    'western_abandonment',
    'corruption_accusation',
]

# Minimum text length to analyze
MIN_TEXT_LENGTH = 30
