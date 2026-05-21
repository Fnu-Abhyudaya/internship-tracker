"""Keyword and location matching for filtering job postings."""

# Full list of role keywords to match against
ROLE_KEYWORDS = [
    'mechanical engineer', 'mechanical engineering',
    'mechanical intern', 'mechanical engineering intern',
    'mechanical design', 'mechanical design engineer',
    'me intern', 'hardware engineer', 'hardware engineering',
    'hardware intern', 'product design engineer',
    'product designer', 'cad engineer', 'design engineer',
    'design engineering', 'r&d engineer',
    'research and development engineer', 'manufacturing engineer',
    'manufacturing engineering', 'manufacturing intern',
    'production engineer', 'production engineering',
    'process engineer', 'process engineering',
    'quality engineer', 'quality engineering',
    'reliability engineer', 'reliability engineering',
    'test engineer', 'testing engineer', 'test engineering',
    'validation engineer', 'validation engineering',
    'simulation engineer', 'fea engineer',
    'finite element analysis', 'cfd engineer',
    'computational fluid dynamics', 'thermal engineer',
    'thermal engineering', 'thermal management',
    'structural engineer', 'structural engineering',
    'stress engineer', 'stress engineering',
    'materials engineer', 'materials engineering',
    'mechatronics', 'mechatronics engineer',
    'mechatronics engineering', 'robotics engineer',
    'robotics engineering', 'automation engineer',
    'automation engineering', 'systems engineer',
    'systems engineering', 'aeronautical engineer',
    'aerospace engineer', 'aerospace engineering',
    'automotive engineer', 'automotive engineering',
    'hvac engineer', 'hvac engineering',
    'tooling engineer', 'tooling engineering',
    'plant engineer', 'plant engineering',
    'facilities engineer', 'facilities engineering',
    'maintenance engineer', 'project engineer',
    'project engineering', 'engineering intern',
    'engineering co-op', 'mechanical co-op',
    'undergraduate intern', 'graduate intern',
    'intern', 'mechanical', 'coop', 'co-op',
    'fall', 'spring', 'summer',
    '2026', '2027', 'new',
]


# Compact set of search terms used when querying career sites.
# These broad terms catch ~99% of results matching ROLE_KEYWORDS.
SEARCH_KEYWORDS = [
    'intern',
    'mechanical',
    'engineer',
    'design',
    'hardware',
    'manufacturing',
]


# Acceptable US location names
US_LOCATION_TOKENS = [
    'united states', 'united states of america', 'usa', 'u.s.',
    'u.s.a', 'us-', ', us', '(us)', ' us ',
]

# US state names and 2-letter codes for location matching
US_STATES = [
    'alabama', 'alaska', 'arizona', 'arkansas', 'california',
    'colorado', 'connecticut', 'delaware', 'florida', 'georgia',
    'hawaii', 'idaho', 'illinois', 'indiana', 'iowa', 'kansas',
    'kentucky', 'louisiana', 'maine', 'maryland', 'massachusetts',
    'michigan', 'minnesota', 'mississippi', 'missouri', 'montana',
    'nebraska', 'nevada', 'new hampshire', 'new jersey',
    'new mexico', 'new york', 'north carolina', 'north dakota',
    'ohio', 'oklahoma', 'oregon', 'pennsylvania', 'rhode island',
    'south carolina', 'south dakota', 'tennessee', 'texas',
    'utah', 'vermont', 'virginia', 'washington', 'west virginia',
    'wisconsin', 'wyoming', 'district of columbia',
]

US_STATE_CODES = [
    ' al,', ' ak,', ' az,', ' ar,', ' ca,', ' co,', ' ct,',
    ' de,', ' fl,', ' ga,', ' hi,', ' id,', ' il,', ' in,',
    ' ia,', ' ks,', ' ky,', ' la,', ' me,', ' md,', ' ma,',
    ' mi,', ' mn,', ' ms,', ' mo,', ' mt,', ' ne,', ' nv,',
    ' nh,', ' nj,', ' nm,', ' ny,', ' nc,', ' nd,', ' oh,',
    ' ok,', ' or,', ' pa,', ' ri,', ' sc,', ' sd,', ' tn,',
    ' tx,', ' ut,', ' vt,', ' va,', ' wa,', ' wv,', ' wi,',
    ' wy,', ' dc,',
]


def matches_role_keywords(title: str) -> bool:
    """Check if a job title contains any of the target keywords."""
    if not title:
        return False
    lower = title.lower()
    for kw in ROLE_KEYWORDS:
        if kw in lower:
            return True
    return False


def is_us_location(location: str) -> bool:
    """Check if a location string represents a US location."""
    if not location or location.lower() == 'n/a':
        # If location unknown, include (benefit of doubt)
        return True

    lower = ' ' + location.lower() + ' '

    # Check direct US mentions
    for token in US_LOCATION_TOKENS:
        if token in lower:
            return True

    # Check state names
    for state in US_STATES:
        if state in lower:
            return True

    # Check state codes (with comma)
    for code in US_STATE_CODES:
        if code in lower:
            return True

    # Check state codes at end of string
    parts = location.replace(',', ' ').split()
    for part in parts:
        if len(part) == 2:
            code = part.upper()
            state_2letter = [
                'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE',
                'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS',
                'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
                'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY',
                'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
                'WI', 'WY', 'DC',
            ]
            if code in state_2letter:
                return True

    return False
