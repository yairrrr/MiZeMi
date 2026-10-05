"""Type-ahead completions for profile fields from the offline reference names.

Suggestions only help a player spell a name the knowledge base already
knows; they never classify, score or store anything. Each suggestion is a
name the resolver maps back to the same entity, so picking one gives the
question engine a recognized answer.
"""

from app.domain.questions.knowledge import KnowledgeBase, KnownEntity, normalize_name
from app.domain.questions.name_matching import fold_hebrew_spelling, script

MAX_SUGGESTIONS = 5
MAX_QUERY_LENGTH = 60

# Bigger, more administrative places first: "קריית" should surface cities
# before hamlets that happen to have a shorter name.
_LOCALITY_RANK = {'PPLC': 0, 'PPLA': 1, 'PPLA2': 2, 'PPLA3': 3, 'PPL': 4, '': 5}


def _key(name: str) -> str:
    # קרית/קריית and similar full/defective spellings complete each other.
    return fold_hebrew_spelling(normalize_name(name))


class SuggestionIndex:
    """Per-kind prefix search, built lazily on the first query for a kind."""

    def __init__(self, knowledge: KnowledgeBase) -> None:
        self._knowledge = knowledge
        self._names: dict[str, tuple[tuple[str, bool, str, KnownEntity], ...]] = {}

    def warm(self, kinds) -> None:
        for kind in kinds:
            self._entries(kind)

    def _entries(self, kind: str) -> tuple[tuple[str, bool, str, KnownEntity], ...]:
        entries = self._names.get(kind)
        if entries is None:
            rows = []
            for entity in self._knowledge.in_kind(kind):
                for primary, name in ((True, entity.english), (True, entity.hebrew),
                                      *((False, alias) for alias in entity.aliases)):
                    key = _key(name)
                    if key:
                        rows.append((key, primary, name, entity))
            entries = self._names[kind] = tuple(rows)
        return entries

    def _display(self, kind: str, entity: KnownEntity, matched: str, hebrew: bool) -> str | None:
        """The typed-against name, or another in the query's script, that resolves back to this entity."""
        preferred = entity.hebrew if hebrew else entity.english
        for name in (matched, preferred, *entity.aliases):
            if name and (script(normalize_name(name)) == 'he') == hebrew:
                resolution = self._knowledge.resolve(kind, name)
                if resolution.entity is not None and resolution.entity.canonical_id == entity.canonical_id:
                    return name
        return None

    def suggest(self, kind: str, text: str, limit: int = MAX_SUGGESTIONS) -> list[str]:
        if not isinstance(text, str) or len(text) > MAX_QUERY_LENGTH:
            return []
        query = _key(text)
        if not query:
            return []
        word_query = ' ' + query
        best: dict[str, tuple] = {}
        for key, primary, name, entity in self._entries(kind):
            if key.startswith(query):
                tier = 0
            elif word_query in key:
                tier = 1
            else:
                continue
            # A name known in both languages is a rough proxy for a well-known entity.
            rank = (tier, not primary, not (entity.english and entity.hebrew),
                    _LOCALITY_RANK.get(entity.locality_type, 5), len(key), key)
            current = best.get(entity.canonical_id)
            if current is None or rank < current[0]:
                best[entity.canonical_id] = (rank, name, entity)

        hebrew = script(query) == 'he'
        suggestions: list[str] = []
        seen: set[str] = set()
        for _, matched, entity in sorted(best.values(), key=lambda item: item[0]):
            name = self._display(kind, entity, matched, hebrew)
            if name is None or normalize_name(name) in seen:
                continue
            seen.add(normalize_name(name))
            suggestions.append(name)
            if len(suggestions) >= limit:
                break
        return suggestions
