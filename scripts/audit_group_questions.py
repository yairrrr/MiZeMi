#!/usr/bin/env python3
"""Reproducible offline sample games for human question-style review."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import QuestionGenerator
from app.infrastructure.knowledge import BUNDLE_DIR, load_knowledge

FIELDS = ('city', 'favorite_food', 'hobby', 'favorite_music', 'favorite_movie', 'age')
NAMES = ('דנה', 'עומר', 'נועה', 'עמית', 'ליאור', 'יעל', 'איתי', 'רוני')
GROUPS = {
    'new_class': [
        ('תל אביב', 'פיצה', 'ריצה', 'Mizrahi', 'המסור', 20),
        ('רמת גן', 'פסטה', 'כדורגל', 'Pop', 'לזמן את הרוע', 22),
        ('ראשון לציון', 'לזניה', 'גלישה', 'Rock', 'שרק', 24),
        ('חיפה', 'סושי', 'גיימינג', 'Mizrahi', 'טיטניק (סרט, 1997)', 21),
        ('באר שבע', 'פלאפל', 'גינון', 'Trance', 'שרק 2', 23),
    ],
    'creative_workshop': [
        ('חיפה', 'סושי', 'ציור', 'Rock', 'שרק', 25),
        ('קריית שמונה', 'ראמן', 'גיטרה', 'Pop', 'צעצוע של סיפור', 27),
        ('חיפה', 'פיצה', 'צילום', 'Rock', 'מוצאים את נמו', 26),
        ('תל אביב', 'פסטה', 'פילאטיס', 'Jazz', 'שרק 2', 28),
        ('רמת גן', 'פלאפל', 'כדורגל', 'Pop', 'המסור', 24),
        ('ירושלים', 'סושי', 'אפייה', 'Rock', 'טיטניק (סרט, 1997)', 29),
    ],
    'mixed_interests': [
        ('תל אביב', 'פיצה', 'כדורגל', 'Mizrahi', 'המסור', 19),
        ('רחובות', 'סושי', 'גלישה', 'Mizrahi', 'לזמן את הרוע', 20),
        ('ראשון לציון', 'לזניה', 'ריצה', 'Rock', 'שרק', 21),
        ('רמת גן', 'פלאפל', 'גיטרה', 'Pop', 'מוצאים את נמו', 22),
        ('באר שבע', 'המבורגר', 'גיימינג', 'Jazz', 'טיטניק (סרט, 1997)', 23),
        ('אילת', 'פסטה', 'פילאטיס', 'Trance', 'שרק 2', 24),
        ('חיפה', 'סושי', 'צילום', 'Rock', 'צעצוע של סיפור', 25),
        ('קריית שמונה', 'פיצה', 'ציור', 'Pop', 'סרט מקומי שלא נמצא במאגר', 26),
    ],
}
ARTISTS=('עומר אדם','עדן בן זקן','Taylor Swift','Metallica','Coldplay')
SONGS=('Shake It Off - Taylor Swift','Blank Space','Enter Sandman','Yellow - Coldplay','Paradise - Coldplay')
GROUPS['music_circle']=[{**dict(zip(FIELDS,row)),'favorite_artist':ARTISTS[i],'favorite_song':SONGS[i]}
                        for i,row in enumerate(GROUPS['new_class'])]


def profile_values(row):
    return dict(row) if isinstance(row,dict) else dict(zip(FIELDS,row))


def profiles(rows, language):
    from app.domain.questions.dataset import ProfileDataset
    players=[]
    for i, row in enumerate(rows):
        pid=f'p{i}'
        fields=tuple(ProfileField(k, v, True) for k, v in profile_values(row).items())
        players.append(Player(pid, NAMES[i % len(NAMES)] + (str(i) if i >= 8 else ''),
                              profile=PlayerProfile(pid, fields)))
    return ProfileDataset(players, language=language)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',type=Path,default=BUNDLE_DIR)
    parser.add_argument('--output',type=Path,default=ROOT/'scripts/knowledge/group-games.json')
    args=parser.parse_args()
    kb=load_knowledge(args.bundle); engine=QuestionGenerator(knowledge=kb)
    games=[]
    for group_index,(name,rows) in enumerate(GROUPS.items()):
        for language in ('he','en'):
            questions=engine.generate(profiles(rows,language),question_count=20,time_limit_seconds=20,seed=41+group_index)
            games.append({'group':name,'language':language,'seed':41+group_index,
                          'profiles':[profile_values(row) for row in rows],
                          'rules':dict(Counter(q.source_rule_id for q in questions)),
                          'questions':[{'number':i+1,'rule':q.source_rule_id,'difficulty':q.difficulty.value,
                                        'text':q.text,'options':[o.text for o in q.options],
                                        'correct':next(o.text for o in q.options if o.option_id==q.correct_option_id),
                                        'explanation':q.explanation} for i,q in enumerate(questions)]})
    args.output.write_text(json.dumps({'version':kb.version,'synthetic':True,'games':games},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps([{'group':g['group'],'language':g['language'],'count':len(g['questions'])} for g in games]))


if __name__=='__main__': main()
