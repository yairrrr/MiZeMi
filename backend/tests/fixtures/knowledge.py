"""Small manually understood classroom; all profile content is synthetic."""
from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions.dataset import ProfileDataset

FIELDS = ('city','favorite_food','hobby','favorite_music','favorite_movie','age')
ROWS = [
    ('Haifa','Pizza','Running','Mizrahi','Saw',20),
    ('Tel Aviv','Sushi','Football','Mizrahi','The Conjuring',22),
    ('Rehovot','Spaghetti','Surfing','Rock','Toy Story',24),
    ('Rishon LeZion','Lasagna','Guitar','Pop','Finding Nemo',26),
    ('Beersheba','Falafel','Photography','Jazz','Titanic (1997 film)',28),
]
NAMES = ('Dana','Omer','Noa','Amit','Lior')
HE_NAMES = ('דנה','עומר','נועה','עמית','ליאור')


def dataset(rows=ROWS, language='en', hidden=()):
    players=[]
    for i,row in enumerate(rows):
        values=dict(row) if isinstance(row,dict) else dict(zip(FIELDS,row))
        pid=f'p{i}'
        fields=tuple(ProfileField(key,value,key not in hidden) for key,value in values.items())
        name=(HE_NAMES if language=='he' else NAMES)[i] if i<5 else f'Player{i+1}'
        players.append(Player(pid,name,profile=PlayerProfile(pid,fields)))
    return ProfileDataset(players,language=language)


def correct(candidate):
    return next(o.text for o in candidate.options if o.option_id==candidate.correct_option_id)
