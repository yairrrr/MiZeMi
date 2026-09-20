"""Knowledge-backed full games, private active frames, reconnect and storage."""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.infrastructure.database import Base, create_database_engine, create_session_factory
from app.infrastructure.database.models import GameRow, GameQuestionRow, QuestionOptionRow
from app.infrastructure.repositories import SqlAlchemyGameRepository
from tests.fixtures.knowledge import ROWS, FIELDS, NAMES
from tests.fixtures.live import host_ws, player_ws, receive_until
from tests.integration.test_game_flow_hardening import Table, _app


@pytest.mark.parametrize('language',['en','he'])
def test_twenty_round_knowledge_game_reconnects_and_persists_explanations(language):
    app=_app()
    with TestClient(app) as client, Table(client,app,names=NAMES,config={'question_count':20,'language':language}) as table:
        table.profiles={name:dict(zip(FIELDS,row)) for name,row in zip(NAMES,ROWS)}
        active=table.start()
        explanations=[]
        for index in range(20):
            current=table.game.current_question
            assert 'correct_option_id' not in active
            assert 'explanation' not in active and 'knowledge_version' not in active
            with host_ws(client,table.room) as restored:
                snapshot=receive_until(restored,'room.updated')['payload']
                question=receive_until(restored,'question.started')['payload']
                assert not {'explanation','correct_option_id','knowledge_version'} & snapshot.keys()
                assert not {'explanation','correct_option_id','knowledge_version'} & question.keys()
            # Deliberately alternate correctness, checking points still come
            # only from the authoritative answer and existing scoring policy.
            for i,name in enumerate(NAMES): table.answer(name,correct=(i==index%len(NAMES)))
            ended=receive_until(table.host,'question.ended')['payload']
            assert ended['explanation']==current.explanation
            assert ended['correct_option_id']==current.correct_option_id
            assert ended['statistics']['answered_count']==5
            assert 'knowledge_version' not in ended
            if current.knowledge_version: explanations.append(current)
            with player_ws(client,table.room.room_code,table.players[NAMES[0]]) as restored:
                receive_until(restored,'room.updated')
                own=receive_until(restored,'question.ended')['payload']
                assert own['explanation']==ended['explanation']
                assert own['player_result']['is_correct']==(index%5==0)
                assert 'host_token' not in json.dumps(own)
            table.host_send('game.next');receive_until(table.host,'leaderboard.updated')
            # Leaderboard reconnect keeps the existing stage-specific protocol.
            if index==19:
                with host_ws(client,table.room) as restored:
                    receive_until(restored,'room.updated')
                    board=receive_until(restored,'leaderboard.updated')['payload']
                    assert len(board['entries'])==5
            table.host_send('game.next')
            if index<19: active=receive_until(table.host,'question.started')['payload']
        finished=receive_until(table.host,'game.finished')['payload']
        assert finished['winners']
        assert len(explanations)>=10
        cross_domain={'group_intersection_count','group_filtered_mode','region_hobby_diversity',
                      'group_subgroup_comparison','intersection_person','song_artist_link'}
        assert len(cross_domain & {q.source_rule_id for q in table.game.questions})>=2
        app.state.game_hub.flush_persistence()
        with app.state.database.session_factory() as session:
            repo=SqlAlchemyGameRepository(session)
            record=repo.get(table.room.game_id)
            assert [q.explanation for q in record.questions]==[q.explanation for q in table.game.questions]
            assert [q.knowledge_version for q in record.questions]==[q.knowledge_version for q in table.game.questions]
            assert sum(bool(q.explanation) for q in record.questions)==len(explanations)
            assert {s.player_id:s.total_score for s in record.scores}==table.game.scores
            repo.delete(table.room.game_id);session.commit()
            assert not session.scalars(select(Base.metadata.tables['question_explanations'])).all()


def test_existing_question_rows_need_no_destructive_migration():
    engine=create_database_engine('sqlite://')
    old_tables=[t for t in Base.metadata.sorted_tables if t.name!='question_explanations']
    Base.metadata.create_all(engine,tables=old_tables)
    factory=create_session_factory(engine)
    # Historical row inserted before the additive table exists.
    with factory() as session:
        game=GameRow(game_id='old',state='FINISHED',current_question_index=0)
        game.questions.append(GameQuestionRow(question_id='old-q',game_id='old',index=0,total_questions=1,
            question_type='multiple_choice',text='Old question',correct_option_id='a',time_limit_seconds=20,
            options=[QuestionOptionRow(question_id='old-q',option_id='a',position=0,text='Old answer')]))
        session.add(game);session.commit()
    Base.metadata.create_all(engine)
    with factory() as session:
        record=SqlAlchemyGameRepository(session).get('old')
        assert record.questions[0].explanation==''
        assert record.questions[0].knowledge_version==''
        assert record.questions[0].text=='Old question'
    engine.dispose()
