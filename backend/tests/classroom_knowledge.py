"""Offline oracle for the *finished* Playwright quiz; never imported by the app.

The browser supplies only public result frames. We correlate them with the
local test database and an internal trace, without adding metadata to the API.
Expected memberships come from a reviewed fixture, not the question rules.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select

from app.application.gameplay import seed_for_game
from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import ProfileDataset, QuestionGenerator
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.database.models import GameQuestionRow
from app.infrastructure.knowledge import get_knowledge
from app.infrastructure.repositories import SqlAlchemyGameRepository

FIXTURE = json.loads((BACKEND.parent / 'frontend/e2e/fixtures/knowledge-room.json').read_text())
FIELDS = ('city', 'favorite_food', 'hobby', 'favorite_music', 'age', 'favorite_movie',
          'favorite_artist', 'favorite_song')
MEDIA = {'movie', 'artist', 'song'}
TECHNICAL = re.compile(r'rule_id|question_family|semantic_key|metadata|SQL|database|ontology|'
                       r'knowledge_version|מאגר|מסד נתונים|טקסונומיה|אונטולוגיה|אלגוריתם', re.I)


def fixture_players():
    return [Player(f'p{i}', row[0], profile=PlayerProfile(f'p{i}', tuple(
        ProfileField(key, int(value) if key == 'age' else value, True)
        for key, value in zip(FIELDS, row[1:])
    ))) for i, row in enumerate(FIXTURE['profiles'])]


def verify_trace(trace, players):
    """Check selected facts by independently counting the fixture's memberships."""
    kb = get_knowledge()
    assert [p.display_name for p in players] == [r[0] for r in FIXTURE['profiles']]
    ids = [p.player_id for p in players]
    names = {p.player_id: p.display_name for p in players}
    members = {dim: {category: {ids[i] for i, facts in enumerate(rows) if category in facts}
                     for category in set().union(*map(set, rows))}
               for dim, rows in FIXTURE['facts'].items()}
    kinds = Counter(dict(c.metadata)['kind'] for c in trace.selected)
    semantic = [(q, c) for q, c in zip(trace.questions, trace.selected)
                if dict(c.metadata)['kind'] == 'semantic']
    assert len(trace.questions) == 20
    assert len(semantic) >= 9, 'At least 45% of the final quiz must derive group categories'
    assert kinds['cross_domain'] >= 2 and kinds['geographic'] >= 2
    assert MEDIA | {'hobby', 'food'} <= {dict(c.metadata)['domain'] for _, c in semantic}

    rows = []
    for q, c in zip(trace.questions, trace.selected):
        meta = dict(c.metadata)
        answer = next(o.text for o in q.options if o.option_id == q.correct_option_id)
        rows.append(dict(index=q.index, question_id=q.question_id, rule=q.source_rule_id,
                         family=meta['family'], kind=meta['kind'], domains=meta.get('domains', meta['domain']).split(','),
                         text=q.text, options=[o.text for o in q.options], answer=answer, explanation=q.explanation))
        assert not TECHNICAL.search(q.text + q.explanation)
        if meta['kind'] == 'direct':
            continue
        assert q.explanation.strip() and re.search('[א-ת]', q.explanation)
        assert all(ch.isprintable() for ch in q.explanation)
        # Geography distance has separate coordinate tests. Count/rank and
        # cross-domain questions here use only the independent fixture facts.
        family, dim, *args = c.semantic_key
        if dim not in members:
            assert meta['kind'] == 'geographic'
            continue
        groups = members[dim]
        counts = {category: len(people) for category, people in groups.items()}
        expected = None
        if family in ('SEMANTIC_COUNT', 'GEO_REGION_COUNT'):
            expected = str(counts.get(args[0], 0))
        elif family in ('SEMANTIC_DIVERSITY', 'GEO_REGION_DIVERSITY'):
            expected = str(len(groups))
        elif family in ('SEMANTIC_UNIQUE', 'GEO_REGION_UNIQUE'):
            people = (set().union(*(v for v in groups.values() if len(v) == 1))
                      if args[0] == 'exclusive_genres' else groups[args[0]])
            assert len(people) == 1
            expected = next(iter(people))
        elif family in ('SEMANTIC_MAJORITY', 'GEO_REGION_MAJORITY', 'SEMANTIC_COMPARISON',
                        'GEO_REGION_COMPARISON', 'SEMANTIC_DISTRIBUTION', 'SEMANTIC_MINORITY'):
            compared = list(counts) if family in ('SEMANTIC_MAJORITY', 'GEO_REGION_MAJORITY') else args
            ordered = sorted(compared, key=lambda key: counts.get(key, 0), reverse=family != 'SEMANTIC_MINORITY')
            assert len(ordered) >= 2 and counts.get(ordered[0], 0) != counts.get(ordered[1], 0), 'A scored rank must be decisive'
            expected = ordered[0]
        elif family in ('CROSS_SUBGROUP_MAJORITY', 'CROSS_SUBGROUP_COMPARISON'):
            condition, target, *compared = args
            subgroup = groups[condition]
            target_counts = {key: len(people & subgroup) for key, people in members[target].items()}
            ordered = sorted(compared or target_counts, key=lambda key: target_counts.get(key, 0), reverse=True)
            assert len(subgroup) >= 3 and target_counts[ordered[0]] > target_counts.get(ordered[1], 0)
            expected = ordered[0]
        elif family == 'CROSS_INTERSECTION_COUNT':
            # Key order: first dimension, its category, second dimension, its category.
            category, target, other = args
            expected = str(len(groups[category] & members[target][other]))
        else:
            assert meta['kind'] == 'geographic', f'Add an independent oracle for {family}'
            continue
        assert meta['answer_key'] == expected, f'{q.text}: incorrect classification/count'
        if expected in names:
            assert answer == names[expected]
        elif expected.isdecimal():
            assert answer == expected
        elif meta['domain'] in MEDIA:
            assert answer == kb.categories[expected].label('he')
    # The fixture deliberately separates declared music (Mizrahi) from the
    # genres derived from submitted artists/songs (Pop). A direct question
    # about favorite_music cannot satisfy these media checks.
    for domain in ('artist', 'song'):
        leaders = [(q, c) for q, c in semantic if dict(c.metadata)['domain'] == domain
                   and c.source_rule_id == 'group_mode']
        assert len(leaders) == 1 and dict(leaders[0][1].metadata)['answer_key'] == 'music.pop'
        assert next(o.text for o in leaders[0][0].options if o.option_id == leaders[0][0].correct_option_id) == 'פופ'
        assert re.search(r'4\s+אנשים', leaders[0][0].explanation)
        assert re.search(r'יותר|מוביל|נפוץ', leaders[0][0].explanation)
    return dict(kinds=dict(kinds), semantic_rounds=len(semantic), questions=rows)


def verify_finished_quiz(results):
    engine = create_database_engine(f'sqlite:///{BACKEND.parent / "frontend/.e2e.db"}')
    try:
        with create_session_factory(engine)() as session:
            game_id = session.scalar(select(GameQuestionRow.game_id).where(
                GameQuestionRow.question_id == results[0]['question_id']))
            assert game_id, 'Finished game has not been persisted yet'
            record = SqlAlchemyGameRepository(session).get(game_id)
        assert record.state == 'FINISHED' and len(record.questions) == len(results) == 20
        players = []
        for p, expected in zip(record.players, fixture_players()):
            fields = tuple(ProfileField(f.field_key, f.value, f.allow_question_usage) for f in p.profile_fields)
            profile = PlayerProfile(p.player_id, fields)
            assert {f.field_key: f.value for f in profile.consented_fields()} == {
                f.field_key: f.value for f in expected.profile.fields}
            players.append(Player(p.player_id, p.display_name, profile=profile))
        dataset = ProfileDataset(players, language='he')
        generator = QuestionGenerator(knowledge=get_knowledge())
        kwargs = dict(question_count=20, time_limit_seconds=20, seed=seed_for_game(game_id))
        trace = generator.trace(dataset, **kwargs)
        assert trace == generator.trace(dataset, **kwargs), 'Identical seed/data must be deterministic'
        for public, stored, generated in zip(results, record.questions, trace.questions):
            for field in ('question_id', 'text', 'correct_option_id', 'explanation'):
                assert public.get(field, '') == getattr(stored, field) == getattr(generated, field)
            assert public['options'] == [dict(option_id=o.option_id, text=o.text) for o in generated.options]
        return dict(seed=kwargs['seed'], deterministic=True, **verify_trace(trace, players))
    finally:
        engine.dispose()


if __name__ == '__main__':
    print(json.dumps(verify_finished_quiz(json.load(sys.stdin)), ensure_ascii=False, indent=2))
