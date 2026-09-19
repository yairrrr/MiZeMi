"""Pure, bounded candidate search over local names; never a best-guess API.

The index narrows by script, length and shared bigrams before edit distance.
It holds reference names only, never player inputs or a cross-room query cache.
"""
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class MatchingPolicy:
    latin_min: int = 6
    hebrew_min: int = 5
    similarity: float = .82
    margin: float = .08
    partial: bool = False


POLICIES = {
    'movies': MatchingPolicy(latin_min=7, partial=True),
    'songs': MatchingPolicy(latin_min=7, hebrew_min=6, partial=True),
    'artists': MatchingPolicy(latin_min=7, partial=True),
    'music': MatchingPolicy(),
    'foods': MatchingPolicy(latin_min=5),
    'hobbies': MatchingPolicy(),
    'localities': MatchingPolicy(),
}
MAX_SEARCH_LENGTH = 64
SIMILARITY_LENGTH_CAP = 20
MAX_CANDIDATES = 256
STOP_WORDS = frozenset(('the', 'a', 'an', 'of', 'and', 'to', 'in', 'on', 'for', 'with'))
_FINALS = str.maketrans('ךםןףץ', 'כמנפצ')
_ENDING = re.compile(r'[ךםןףץ](?=\s|$)')
_DOUBLED = re.compile(r'(?<=[א-ת])(וו|יי)(?=[א-ת])')
_NUMBERS = re.compile(r'\d+')


def fold_hebrew_spelling(key: str) -> str:
    """Collapse doubled vav/yod only between Hebrew letters."""
    return _DOUBLED.sub(lambda m: m[0][0], key)


def spelling_key(key: str) -> str:
    """Only Hebrew full/defective spelling and word-final letter forms."""
    return _ENDING.sub(lambda m: m[0].translate(_FINALS), fold_hebrew_spelling(key))


def script(key: str) -> str:
    kinds = set()
    for c in key:
        if c.isalpha():
            kinds.add('he' if 'א' <= c <= 'ת' else 'latin' if 'LATIN' in unicodedata.name(c, '') else 'other')
    return next(iter(kinds)) if len(kinds) == 1 else 'mixed'


def bigrams(key: str) -> frozenset[str]:
    return frozenset(key[i:i+2] for i in range(len(key)-1))


def character_mask(key: str) -> int:
    """Lossy presence mask: collisions only admit extra candidates, never hide one."""
    mask = 0
    for c in key:
        mask |= 1 << (ord(c) % 64)
    return mask


def protected_tokens(key: str, kind: str) -> tuple:
    # Sequels/years cannot be "corrected" into another film or recording.
    roman = tuple(t for t in key.split() if re.fullmatch('[ivxlcdm]+', t)) if kind in ('movies', 'songs') else ()
    return tuple(_NUMBERS.findall(key)), roman


def bounded_distance(a: str, b: str, limit: int = 2) -> int:
    """Banded optimal-string-alignment distance, including adjacent swaps.

    Return limit+1 outside the radius; O(length * limit), not a full matrix.
    The second edit is examined only to reject a near runner-up, not accepted.
    """
    if abs(len(a)-len(b)) > limit:
        return limit+1
    previous = list(range(len(b)+1))
    older = None
    for i, char in enumerate(a, 1):
        row = [limit+1] * (len(b)+1)
        row[0] = i
        for j in range(max(1, i-limit), min(len(b), i+limit)+1):
            row[j] = min(previous[j]+1, row[j-1]+1, previous[j-1]+(char != b[j-1]))
            if older is not None and j > 1 and char == b[j-2] and a[i-2] == b[j-1]:
                row[j] = min(row[j], older[j-2]+1)
        if min(row) > limit:
            return limit+1
        older, previous = previous, row
    return min(previous[-1], limit+1)


class NameSearch:
    """Compact immutable postings; integer arrays share normalized name strings."""

    def __init__(self, names, kind: str, gram_pool: dict[str, str] | None = None):
        self.kind = kind
        self.policy = POLICIES[kind]
        self.names = tuple(sorted(names))
        self.masks = array('Q', (character_mask(key) for key in self.names))
        gram_pool = {} if gram_pool is None else gram_pool
        id_type = 'H' if len(self.names) <= 65536 else 'I'
        postings = defaultdict(lambda: defaultdict(lambda: array(id_type)))
        folded, articles = defaultdict(list), defaultdict(list)
        for index, key in enumerate(self.names):
            if any('א' <= c <= 'ת' for c in key):
                alternate = spelling_key(key)
                if alternate != key:
                    folded[alternate].append(key)
            if self.policy.partial:
                for article in ('the ', 'a ', 'an '):
                    if key.startswith(article):
                        articles[key[len(article):]].append(key)
                        break
            # Long names still block ambiguous partials and act as fuzzy
            # competitors near the query-length boundary.
            if len(key) < 5:
                continue
            language = script(key)
            if language not in ('he', 'latin', 'mixed'):
                continue
            bucket = postings[language, len(key)]
            for gram in sorted(bigrams(key)):
                bucket[gram_pool.setdefault(gram, gram)].append(index)
        # One packed read-only ID buffer, not hundreds of thousands of tiny arrays.
        ids = array(id_type)
        self.postings = {}
        for scope, grams in postings.items():
            packed = {}
            for gram, entries in grams.items():
                packed[gram] = (len(ids) << 32) | len(entries)
                ids.extend(entries)
            self.postings[scope] = packed
        self.ids = memoryview(ids.tobytes()).cast(id_type)
        self.folded = dict(folded)
        self.articles = dict(articles)

    def posting(self, bucket, gram):
        span = bucket.get(gram, 0)
        start, size = span >> 32, span & 0xffffffff
        return self.ids[start:start+size]

    def spelling_names(self, key: str) -> tuple[str, ...]:
        folded = spelling_key(key)
        return tuple(dict.fromkeys((folded, *self.folded.get(folded, ()))))

    def partial_names(self, key: str) -> tuple[str, ...] | None:
        """None means too broad to evaluate safely, not an empty candidate set."""
        if not self.policy.partial or not 7 <= len(key) <= MAX_SEARCH_LENGTH:
            return ()
        if key in self.articles:
            return tuple(self.articles[key])
        tokens = tuple(t for t in key.split() if t not in STOP_WORDS)
        if len(tokens) < 2 or not all(t.isalpha() for t in tokens):
            return ()
        # Any full-word partial match must contain every within-word bigram.
        # Use the rarest posting, across lengths, before checking whole tokens.
        grams = set().union(*(bigrams(t) for t in tokens))
        if not grams:
            return ()
        language = script(key)
        buckets = [bucket for (lang, _), bucket in self.postings.items() if lang in (language, 'mixed')]
        gram = min(grams, key=lambda g: (sum(b.get(g, 0) & 0xffffffff for b in buckets), g))
        indices = {i for bucket in buckets for i in self.posting(bucket, gram)}
        found = []
        for i in sorted(indices):
            name = self.names[i]
            words = tuple(t for t in name.split() if t not in STOP_WORDS)
            # Full tokens, in order; neither a word fragment nor reordered words.
            if any(words[start:start+len(tokens)] == tokens for start in range(len(words)-len(tokens)+1)):
                found.append(name)
                if len(found) > MAX_CANDIDATES:
                    return None
        return tuple(found)

    def partial_is_strong(self, key: str, name: str) -> bool:
        if name in self.articles.get(key, ()):
            return True
        entered = ''.join(t for t in key.split() if t not in STOP_WORDS)
        reference = ''.join(t for t in name.split() if t not in STOP_WORDS)
        return (protected_tokens(key, self.kind) == protected_tokens(name, self.kind)
                and len(entered) >= .8 * len(reference))

    def fuzzy_names(self, key: str) -> tuple[tuple[str, int, float], ...] | None:
        language = script(key)
        minimum = self.policy.hebrew_min if language == 'he' else self.policy.latin_min
        if language not in ('he', 'latin') or not minimum <= len(key.replace(' ', '')) <= MAX_SEARCH_LENGTH:
            return ()
        if len(key) > MAX_SEARCH_LENGTH:
            return ()
        grams = bigrams(key)
        counts = Counter()
        for length in range(max(5, len(key)-2), len(key)+3):
            bucket = self.postings.get((language, length), {})
            for gram in sorted(grams):
                counts.update(self.posting(bucket, gram))
        # Two adjacent swaps can destroy at most six distinct bigrams.
        threshold = max(1, len(grams)-6)
        protected = protected_tokens(key, self.kind)
        mask = character_mask(key)
        indices = [i for i, count in counts.items() if count >= threshold
                   and (mask ^ self.masks[i]).bit_count() <= 4
                   and len(self.names[i].replace(' ', '')) >= minimum
                   and protected_tokens(self.names[i], self.kind) == protected]
        if len(indices) > MAX_CANDIDATES:
            return None  # Never truncate: a discarded candidate might be the true runner-up.
        found = []
        for i in sorted(indices):
            name = self.names[i]
            distance = bounded_distance(key, name)
            if distance <= 2:
                # A bounded length denominator prevents an unsearched three-edit
                # contender on a very long title from violating the 0.08 margin.
                # This is a comparison score, not a probability of identity.
                score = 1-distance/min(max(len(key), len(name)), SIMILARITY_LENGTH_CAP)
                found.append((name, distance, score))
        return tuple(found)
