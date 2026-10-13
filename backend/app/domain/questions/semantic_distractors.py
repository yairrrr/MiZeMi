"""Editorial proximity for plausible options, never evidence for an answer.

Neighbors are not semantic facts or parent genres. Correctness is established
by the rule before this ordering is used. No similarity is inferred about users.
"""
NEIGHBORS = {
    'movie.horror': ('movie.thriller','movie.mystery','movie.crime','movie.fantasy'),
    'movie.thriller': ('movie.mystery','movie.horror','movie.crime','movie.action'),
    'movie.mystery': ('movie.thriller','movie.crime','movie.horror','movie.drama'),
    'movie.action': ('movie.adventure','movie.thriller','movie.superhero','movie.crime'),
    'movie.adventure': ('movie.action','movie.fantasy','movie.scifi','movie.family'),
    'movie.scifi': ('movie.fantasy','movie.adventure','movie.action','movie.mystery'),
    'movie.fantasy': ('movie.scifi','movie.adventure','movie.family','movie.superhero'),
    'movie.comedy': ('movie.romance','movie.family','movie.drama','movie.musical'),
    'movie.drama': ('movie.romance','movie.biographical','movie.crime','movie.thriller'),
    'movie.romance': ('movie.drama','movie.comedy','movie.musical','movie.family'),
    'music.mizrahi': ('music.mediterranean','music.pop','music.folk','music.rock'),
    'music.mediterranean': ('music.mizrahi','music.pop','music.folk','music.latin'),
    'music.israeli': ('music.mizrahi','music.mediterranean','music.pop','music.rock'),
    'music.jewish': ('music.israeli','music.mizrahi','music.folk','music.classical'),
    'music.pop': ('music.rnb','music.rock','music.electronic','music.hiphop'),
    'music.hiphop': ('music.rnb','music.pop','music.reggae','music.funk'),
    'music.rock': ('music.indie','music.metal','music.blues','music.pop'),
    'music.electronic': ('music.house','music.techno','music.trance','music.pop'),
    'music.house': ('music.techno','music.trance','music.electronic','music.disco'),
    'music.techno': ('music.house','music.trance','music.electronic'),
    'music.trance': ('music.techno','music.house','music.electronic'),
    'music.jazz': ('music.blues','music.soul','music.funk','music.classical'),
    'music.rnb': ('music.soul','music.pop','music.hiphop','music.funk'),
    'food.italian': ('food.french','food.greek','food.spanish','food.middle_eastern'),
    'food.japanese': ('food.korean','food.chinese','food.thai','food.asian'),
    'food.chinese': ('food.thai','food.korean','food.japanese','food.asian'),
    'food.middle_eastern': ('food.north_african','food.greek','food.jewish','food.italian'),
    'food.pasta': ('food.rice','food.dumpling','food.bread','food.potato'),
    'food.rice': ('food.pasta','food.legume','food.potato','food.dumpling'),
    'food.bread': ('food.pastry','food.sandwich','food.pasta','food.dumpling'),
    'food.soup': ('food.stew','food.dip','food.salad'),
    'food.dessert': ('food.pastry','food.bread','food.dip'),
    'hobby.sport': ('hobby.fitness','hobby.water','hobby.nature','hobby.table_games'),
    'hobby.creative': ('hobby.music','hobby.digital','hobby.cooking','hobby.collecting'),
    'hobby.music': ('hobby.creative','hobby.digital','hobby.learning'),
    'hobby.nature': ('hobby.travel','hobby.sport','hobby.water','hobby.wellbeing'),
    'place.central': ('place.tel_aviv','place.jerusalem','place.haifa','place.south'),
    'place.tel_aviv': ('place.central','place.jerusalem','place.haifa'),
}


def category_choices(knowledge,dimension,winner,represented=()):
    all_ids=[c.category_id for c in knowledge.categories.values() if c.dimension==dimension]
    order=dict.fromkeys((*NEIGHBORS.get(winner,()),*represented,*all_ids))
    return [winner,*[c for c in order if c!=winner and c in all_ids][:3]]
