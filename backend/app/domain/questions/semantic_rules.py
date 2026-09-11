"""Bounded, explainable rules over positive local facts and mathematics.

Every scored comparison has a unique solution. Missing knowledge never proves
an exclusion. At most 60 candidates per family; classroom-sized pair tables
and clue-product loops capped at 4,000 entries. No IO.
"""
from itertools import combinations, islice
from random import Random

from app.domain.questions.advanced_rules import unique_extreme
from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.language import say
from app.domain.questions.question import Difficulty
from app.domain.questions.rule import QuestionRule
from app.domain.questions.rules import _build_options
from app.domain.questions.semantic import DIMENSIONS, enrich
from app.domain.questions.semantic_distractors import category_choices, NEIGHBORS

MAX_CANDIDATES = 60
MAX_COMPARISONS = 4000
PREFERENCE_DIMENSIONS = tuple(d for d in DIMENSIONS if d != 'place.district')


class SemanticRule(QuestionRule):
    difficulty = Difficulty.MEDIUM
    hops = 2
    rule_id = 'semantic'

    def __init__(self, knowledge):
        self.knowledge = knowledge

    def generate(self, dataset, rng: Random):
        if dataset.player_count < 3:
            return ()
        return tuple(islice(self.candidates(enrich(dataset,self.knowledge),rng),MAX_CANDIDATES))

    def text(self, view, en, he, **values):
        return say(view.dataset.language,en,he,**values)

    def make(self, v, rng, text, answer, choices, dims, explanation, *, key=(), focus=(), people=None):
        choices = list(dict.fromkeys(str(c) for c in choices))
        distractors = [c for c in choices if c != str(answer)]
        if not distractors:
            return
        options, correct = _build_options(str(answer), rng.sample(distractors,min(3,len(distractors))),rng)
        yield QuestionCandidate(text,options,correct,self.rule_id,
            tuple(dict.fromkeys(DIMENSIONS[d][0] for d in dims)),tuple(people or v.ids),
            difficulty=self.difficulty,semantic_key=(self.rule_id,*map(str,key)),
            focus_player_ids=tuple(focus),metadata=(('reasoning_hops',self.hops),),
            explanation=explanation,knowledge_version=self.knowledge.version)

    def categories(self, v, dim, winner):
        return [v.label(c) for c in category_choices(self.knowledge,dim,winner,v.groups(dim))]

    def number(self, v, rng, text, answer, maximum, dims, explanation, **kwargs):
        choices = [n for n in (answer,answer-1,answer+1,answer-2,answer+2) if 0<=n<=maximum]
        yield from self.make(v,rng,text,answer,choices[:4],dims,explanation,**kwargs)

    def clue(self, v, dim, cat):
        en = '{subject} in {category}'
        he = {'movie.genre':'סרטים בז׳אנר {category}', 'music.genre':'מוזיקה בסגנון {category}',
              'food.cuisine':'מאכלים שמזוהים עם {category}', 'food.format':'מאכלים ממשפחת {category}',
              'hobby.family':'תחביבים בתחום {category}', 'place.district':'יישובים ב{category}'}[dim]
        return self.text(v,en,he,subject=v.subject(dim),category=v.label(cat))

    def mode_question(self, v, dim):
        he = {'movie.genre':'איזה ז׳אנר קולנוע חוזר בבחירות של הכי הרבה משתתפים?',
              'music.genre':'איזה סגנון מוזיקה חוזר בבחירות של הכי הרבה משתתפים?',
              'food.cuisine':'איזה מטבח מחבר בין המאכלים של הכי הרבה משתתפים?',
              'food.format':'איזו משפחת מאכלים חוזרת אצל הכי הרבה משתתפים?',
              'hobby.family':'איזו משפחת תחביבים חוזרת אצל הכי הרבה משתתפים?',
              'place.district':'איזה מחוז מיוצג על ידי הכי הרבה משתתפים?'}[dim]
        return self.text(v,'Which of these {dimension} connects the most players’ {subject}?',he,
                         dimension=v.dimension_label(dim),subject=v.subject(dim))

    def discovery(self, v, dim, cat, people):
        return self.text(v,'{works}: {category}. Players who made these choices: {count}.',
                         '{works}: החיבור הוא {category}. מספר המשתתפים שבחרו בהם: {count}.',
                         works=v.evidence(dim,cat,people),category=v.label(cat),count=len(people))


class SemanticCountRule(SemanticRule):
    rule_id = 'semantic_count'
    difficulty = Difficulty.EASY

    def candidates(self,v,rng):
        for dim in PREFERENCE_DIMENSIONS:
            if not v.complete(dim): continue
            for cat, people in v.groups(dim).items():
                if not 1 <= len(people) < len(v.ids): continue
                text=self.text(v,'How many players chose {clue}?', 'כמה משתתפים בחרו {clue}?',clue=self.clue(v,dim,cat))
                yield from self.number(v,rng,text,len(people),len(v.ids),(dim,),self.discovery(v,dim,cat,people),key=(dim,cat),focus=people)


class SemanticSubsetCountRule(SemanticRule):
    """Incomplete rooms can still ask explicitly scoped, consent-safe counts."""
    rule_id = 'semantic_subset_count'

    def candidates(self,v,rng):
        for dim in PREFERENCE_DIMENSIONS:
            if v.complete(dim): continue
            people=tuple(p for p in v.ids if p in v.memberships[dim])[:6]
            if len(people)<3: continue
            for cat,holders in v.groups(dim,people).items():
                if not 0<len(holders)<len(people): continue
                text=self.text(v,'Among {names}, how many chose {clue}?',
                               'מבין {names}, כמה בחרו {clue}?',
                               names=', '.join(v.name(p) for p in people),clue=self.clue(v,dim,cat))
                yield from self.number(v,rng,text,len(holders),len(people),(dim,),
                    self.discovery(v,dim,cat,holders),key=(dim,cat,*people),focus=people,people=people)


class SemanticScopedPairRule(SemanticRule):
    """Only shown, fully resolved alternatives compete; unlisted people do not."""
    rule_id = 'semantic_scoped_pair'
    hops = 3

    def candidates(self,v,rng):
        for dim in PREFERENCE_DIMENSIONS:
            if v.complete(dim): continue
            people=tuple(p for p in v.ids if p in v.memberships[dim])
            if len(people)<3: continue
            pairs=tuple(combinations(people,2))
            for cat in v.groups(dim,people):
                valid=[pair for pair in pairs if all(cat in v.memberships[dim][p] for p in pair)
                       and v.entities(dim)[pair[0]]!=v.entities(dim)[pair[1]]]
                valid_set=set(valid)
                wrong=[pair for pair in pairs if pair not in valid_set]
                if not valid or not wrong: continue
                winner=valid[0]
                text=self.text(v,'Among the pairs below, who picked different {subject} that share {category}?',
                               'מבין הזוגות שמופיעים כאן, מי בחרו {subject} שונים שהחיבור ביניהם הוא {category}?',
                               subject=v.subject(dim),category=v.label(cat))
                yield from self.make(v,rng,text,v.pair_name(winner),[v.pair_name(p) for p in [winner,*wrong]],
                    (dim,),self.discovery(v,dim,cat,winner),key=(dim,cat,*winner),focus=winner,people=people)


class SemanticModeRule(SemanticRule):
    rule_id = 'semantic_mode'

    def candidates(self,v,rng):
        for dim in DIMENSIONS:
            if not v.complete(dim): continue
            counts=v.counts(dim); winner=unique_extreme(counts)
            if winner is None or counts[winner]<2: continue
            text=self.mode_question(v,dim)
            yield from self.make(v,rng,text,v.label(winner),self.categories(v,dim,winner),(dim,),
                                 self.discovery(v,dim,winner,v.groups(dim)[winner]),key=(dim,))


class SemanticRareRule(SemanticRule):
    rule_id = 'semantic_rare'

    def candidates(self,v,rng):
        for dim in PREFERENCE_DIMENSIONS:
            if not v.complete(dim): continue
            counts=v.counts(dim); winner=unique_extreme(counts,smallest=True)
            if winner is None: continue
            # Only represented alternatives: absent categories would all have 0.
            text=self.text(v,'Among the {dimension} represented here, which appears in the fewest players’ {subject}?',
                           'מבין {dimension} שמופיעים כאן, מה חוזר אצל הכי מעט משתתפים לפי ה{subject} שנבחרו?',
                           dimension=v.dimension_label(dim),subject=v.subject(dim))
            yield from self.make(v,rng,text,v.label(winner),[v.label(c) for c in counts],(dim,),
                                 self.discovery(v,dim,winner,v.groups(dim)[winner]),key=(dim,))


class SemanticDiversityRule(SemanticRule):
    rule_id = 'semantic_diversity'
    difficulty = Difficulty.HARD
    hops = 3

    def candidates(self,v,rng):
        for dim in PREFERENCE_DIMENSIONS:
            if not v.complete(dim): continue
            counts={cat:len({v.entities(dim)[p].canonical_id for p in ps}) for cat,ps in v.groups(dim).items()}
            winner=unique_extreme(counts)
            if winner is None or counts[winner]<2: continue
            text=self.text(v,'Count different {subject}, not repeated picks: which of these {dimension} connects the most?',
                           'סופרים {subject} שונים, בלי לספור שוב את אותה בחירה: מה מבין {dimension} הבאים מחבר בין הכי הרבה מהם?',
                           subject=v.subject(dim),dimension=v.dimension_label(dim))
            explanation=self.discovery(v,dim,winner,v.groups(dim)[winner])+' '+self.text(v,
                'That makes {n} different choices in this family.','יחד יש כאן {n} בחירות שונות במשפחה הזאת.',n=counts[winner])
            yield from self.make(v,rng,text,v.label(winner),self.categories(v,dim,winner),(dim,),explanation,key=(dim,))


class SemanticDifferentPairRule(SemanticRule):
    rule_id = 'semantic_different_pair'
    hops = 3

    def candidates(self,v,rng):
        for dim in PREFERENCE_DIMENSIONS:
            if not v.complete(dim): continue
            for cat,ps in v.groups(dim).items():
                if len(ps)!=2 or v.entities(dim)[ps[0]]==v.entities(dim)[ps[1]]: continue
                text=self.text(v,'Which pair picked {clue}, choosing different works or activities?',
                               'איזה זוג בחרו {clue}, אבל כל אחד בחר משהו אחר?',clue=self.clue(v,dim,cat))
                yield from self.make(v,rng,text,v.pair_name(ps),[v.pair_name(pair) for pair in combinations(v.ids,2)],
                                     (dim,),self.discovery(v,dim,cat,ps),key=(dim,cat),focus=ps)


class SemanticIntersectionRule(SemanticRule):
    rule_id = 'semantic_intersection'
    difficulty = Difficulty.HARD
    hops = 3

    def candidates(self,v,rng):
        pairs=(('movie.genre','hobby.family'),('food.cuisine','hobby.family'),('music.genre','movie.genre'),('music.genre','food.format'))
        for a,b in pairs:
            eligible=tuple(p for p in v.ids if p in v.memberships[a] and p in v.memberships[b])
            scoped=len(eligible)!=len(v.ids)
            if scoped: eligible=eligible[:6]
            if len(eligible)<3: continue
            groups_a,groups_b=v.groups(a,eligible),v.groups(b,eligible)
            for ca,cb in islice(((ca,cb) for ca in groups_a for cb in groups_b),MAX_COMPARISONS):
                ga,gb=groups_a[ca],groups_b[cb]
                both=[p for p in ga if p in gb]
                if len(ga)<2 or len(gb)<2 or len(both)!=1: continue
                p=both[0]
                text=self.text(v,'Who connects both clues: {a}, and {b}?',
                               'מי מחבר/ת בין שני הרמזים: {a}, וגם {b}?', a=self.clue(v,a,ca),b=self.clue(v,b,cb))
                if scoped:
                    text=self.text(v,'Among {names}: {question}','מבין {names}: {question}',names=', '.join(v.name(p) for p in eligible),question=text)
                explanation=self.text(v,'{name} connects them: {first}; {second}.',
                    '{name} מחבר/ת ביניהם: {first}; {second}.',name=v.name(p),
                    first=v.evidence(a,ca,[p])+' → '+v.label(ca),second=v.evidence(b,cb,[p])+' → '+v.label(cb))
                yield from self.make(v,rng,text,v.name(p),[v.name(i) for i in eligible],(a,b),explanation,key=(a,ca,b,cb),focus=(p,),people=eligible)


class SemanticFilteredModeRule(SemanticRule):
    rule_id = 'semantic_filtered_mode'
    difficulty = Difficulty.HARD
    hops = 4

    def candidates(self,v,rng):
        for condition,target in (('hobby.family','movie.genre'),('movie.genre','hobby.family'),('music.genre','food.cuisine'),('place.district','hobby.family')):
            if not v.complete(condition,target): continue
            for cat,people in v.groups(condition).items():
                if not 3<=len(people)<len(v.ids): continue
                counts=v.counts(target,people); winner=unique_extreme(counts)
                if winner is None or counts[winner]<2: continue
                text=self.text(v,'Among those who chose {clue}: {question}',
                               'מבין מי שבחרו {clue}, {question}',clue=self.clue(v,condition,cat),question=self.mode_question(v,target))
                explanation=self.discovery(v,condition,cat,people)+' '+self.discovery(v,target,winner,v.groups(target,people)[winner])
                yield from self.make(v,rng,text,v.label(winner),self.categories(v,target,winner),(condition,target),explanation,
                                     key=(condition,cat,target),focus=people,people=people)


class SemanticOutlierRule(SemanticRule):
    rule_id = 'semantic_outlier'
    hops = 3

    def candidates(self,v,rng):
        dim='food.cuisine'
        if not v.complete(dim): return
        # Disjoint *recorded* cuisines are not proof of exclusive cultural
        # ownership. Explicitly ask which choice has the other named cuisine.
        groups=v.groups(dim)
        for cat,people in groups.items():
            if len(people)<3: continue
            for other,others in groups.items():
                if other==cat: continue
                for odd in others:
                    group=(*people[:3],odd)
                    if odd in people or any(p in others for p in people[:3]): continue
                    text=self.text(v,'Three of these players chose foods linked to {first}. Whose choice is linked to {other}?',
                                   'שלושה מהמשתתפים הבאים בחרו מאכלים שמזוהים עם {first}. של מי הבחירה שמזוהה עם {other}?',
                                   first=v.label(cat),other=v.label(other))
                    explanation=self.discovery(v,dim,cat,people[:3])+' '+self.discovery(v,dim,other,[odd])
                    yield from self.make(v,rng,text,v.name(odd),[v.name(p) for p in group],(dim,),explanation,
                                         key=(cat,other,*group),focus=group,people=group)


class MusicArtistBridgeRule(SemanticRule):
    rule_id = 'music_artist_bridge'
    hops = 3

    def candidates(self,v,rng):
        dim='music.genre'
        if not v.complete(dim): return
        counts=v.counts(dim); winner=unique_extreme(counts)
        if winner is None or counts[winner]<2: return
        artists=self.knowledge.in_kind('artists')
        yes=[a for a in artists if winner in a.category_ids]
        no=[a for a in artists if winner not in a.category_ids]
        if not yes or len(no)<3: return
        # Classifications, never "you must listen to X". Pick one positive
        # artist, then ask which has that *listed* classification. Source facts
        # are an explicit finite reference, not exhaustive artist identities.
        artist=yes[rng.randrange(len(yes))]
        nearby=set(NEIGHBORS.get(winner,()))
        neighbors=[a for a in no if a.category_ids & nearby]
        pool=neighbors if len(neighbors)>=3 else no
        others=rng.sample(pool,3)
        text=self.text(v,'Which artist below is listed in the game under the music style chosen most often by this group?',
                       'איזה אמן מהרשימה משויך במשחק לסגנון המוזיקה שחוזר הכי הרבה בבחירות של הקבוצה?')
        explanation=self.text(v,'{style} connects {n} players’ choices. {artist} is classified in that style; the connection is the musical style.',
                              '{style} מחבר בין הבחירות של {n} משתתפים. {artist} מזוהה עם הסגנון הזה. זה החיבור המוזיקלי ביניהם.',
                              style=v.label(winner),n=counts[winner],artist=artist.label(v.dataset.language))
        yield from self.make(v,rng,text,artist.label(v.dataset.language),[a.label(v.dataset.language) for a in [artist,*others]],(dim,),explanation,key=(winner,))


def separated_extreme(scores, *, smallest=False, margin=1.0):
    """Suppress exact/near ties at a meaningful geographic precision."""
    ordered=sorted(scores, key=lambda key:scores[key], reverse=not smallest)
    if len(ordered)<2 or abs(scores[ordered[0]]-scores[ordered[1]])<margin:
        return None
    return ordered[0]


class LocalityExtremeRule(SemanticRule):
    rule_id = 'locality_extreme'
    difficulty = Difficulty.EASY

    def candidates(self,v,rng):
        places=v.rows['city']
        if len(places)!=len(v.ids): return
        latitude={p:e.coordinates[0] for p,e in places.items()}
        for south in (False,True):
            winner=separated_extreme(latitude,smallest=south,margin=.01)
            if winner is None: continue
            direction=self.text(v,'south' if south else 'north','דרומי' if south else 'צפוני')
            text=self.text(v,'Whose town is furthest {direction} in the group?',
                           'של מי היישוב ה{direction} ביותר בקבוצה?',direction=direction)
            explanation=self.text(v,'{town}, chosen by {name}, has the {direction}ernmost reference point among these towns.',
                                   '{town}, היישוב של {name}, הוא היישוב ה{direction} ביותר לפי נקודות הייחוס של היישובים שנבחרו.',
                                   town=places[winner].label(v.dataset.language),name=v.name(winner),direction=direction)
            yield from self.make(v,rng,text,v.name(winner),[v.name(p) for p in v.ids],('place.district',),explanation,key=(south,),focus=(winner,))


class LocalityDistanceRule(SemanticRule):
    rule_id = 'locality_distance_pair'
    difficulty = Difficulty.HARD
    hops = 3

    def candidates(self,v,rng):
        for closest in (True,False):
            pair=separated_extreme(v.distances,smallest=closest)
            if pair is None: continue
            # Distinct towns only for "between towns"; duplicate-town ties are
            # suppressed without pretending player homes are co-located.
            if v.rows['city'][pair[0]]==v.rows['city'][pair[1]]: continue
            adjective=self.text(v,'closest' if closest else 'furthest apart','הקרובים ביותר' if closest else 'הרחוקים ביותר')
            text=self.text(v,'Which pair chose the towns that are {adjective} by air distance?',
                           'איזה זוג בחרו את היישובים {adjective} זה מזה בקו אווירי?',adjective=adjective)
            explanation=distance_explanation(self,v,pair)
            yield from self.make(v,rng,text,v.pair_name(pair),[v.pair_name(p) for p in v.distances],('place.district',),explanation,key=(closest,),focus=pair)


def distance_explanation(rule,v,pair):
    places=v.rows['city']
    return rule.text(v,'{a} and {b} are about {km} km apart by air, comparing locality reference points, not homes or roads.',
                     'בין {a} ל{b} יש כ־{km} ק״מ בקו אווירי, לפי נקודות הייחוס של היישובים ולא לפי כתובות מגורים או כבישים.',
                     a=places[pair[0]].label(v.dataset.language),b=places[pair[1]].label(v.dataset.language),
                     km=round(v.distances.get(pair,v.distances.get(tuple(reversed(pair)),0))))


class LocalityNearestRule(SemanticRule):
    rule_id = 'locality_nearest_to'
    hops = 3

    def candidates(self,v,rng):
        if not v.distances: return
        for anchor in v.ids:
            scores={p:v.distances.get((anchor,p),v.distances.get((p,anchor))) for p in v.ids if p!=anchor}
            winner=separated_extreme(scores,smallest=True)
            if winner is None or v.rows['city'][anchor]==v.rows['city'][winner]: continue
            text=self.text(v,'Whose town is closest to {name}’s town by air distance?',
                           'של מי היישוב הכי קרוב ליישוב של {name} בקו אווירי?',name=v.name(anchor))
            yield from self.make(v,rng,text,v.name(winner),[v.name(p) for p in scores],('place.district',),
                                 distance_explanation(self,v,(anchor,winner)),key=(anchor,),focus=(anchor,winner))


class LocalityMiddleRule(SemanticRule):
    rule_id = 'locality_middle'
    difficulty = Difficulty.HARD
    hops = 3

    def candidates(self,v,rng):
        places=v.rows['city']
        if len(places)!=len(v.ids) or len(places)%2==0: return
        ordered=sorted(places,key=lambda p:places[p].coordinates[0],reverse=True)
        if any(abs(places[a].coordinates[0]-places[b].coordinates[0])<.01 for a,b in zip(ordered,ordered[1:])): return
        winner=ordered[len(ordered)//2]
        text=self.text(v,'If we order everyone’s towns from north to south, who lands exactly in the middle?',
                       'אם מסדרים את היישובים של כולם מצפון לדרום, מי בדיוק באמצע?')
        explanation=self.text(v,'From north to south: {names}. The middle is {name}.',
                              'מצפון לדרום: {names}. באמצע נמצא/ת {name}.',
                              names=' → '.join(places[p].label(v.dataset.language) for p in ordered[:9]),name=v.name(winner))
        # Avoid a truncated ordering that claims to show everyone in a large room.
        if len(ordered)>9:
            explanation=self.text(v,'{n} towns are north of {town} and {n} are south of it.',
                                  '{n} יישובים נמצאים מצפון ל{town} ו־{n} מדרום לו.',n=len(ordered)//2,town=places[winner].label(v.dataset.language))
        yield from self.make(v,rng,text,v.name(winner),[v.name(p) for p in v.ids],('place.district',),explanation,key=('latitude',),focus=(winner,))


class LocalityDistinctRule(SemanticRule):
    rule_id = 'locality_distinct'
    difficulty = Difficulty.EASY

    def candidates(self,v,rng):
        places=v.rows['city']
        if len(places)!=len(v.ids): return
        count=len(set(places.values()))
        if count==len(v.ids): return
        text=self.text(v,'Allowing for different spellings of the same place, how many different towns are represented here?',
                       'גם כשכותבים את אותו המקום בכמה דרכים, כמה יישובים שונים מיוצגים בקבוצה?')
        explanation=self.text(v,'There are {n} different towns. Different spellings of the same town count once.',
                              'יש כאן {n} יישובים שונים. כתיבים שונים של אותו יישוב נספרים פעם אחת.',n=count)
        yield from self.number(v,rng,text,count,len(v.ids),('place.district',),explanation,key=('towns',))


class SemanticNearbyPairRule(SemanticRule):
    rule_id = 'semantic_nearby_pair'
    difficulty = Difficulty.HARD
    hops = 4

    def candidates(self,v,rng):
        if not v.distances: return
        for dim in ('hobby.family','movie.genre','food.cuisine'):
            if not v.complete(dim): continue
            for cat,people in v.groups(dim).items():
                scores={pair:d for pair,d in v.distances.items() if set(pair)<=set(people)
                        and v.entities(dim)[pair[0]]!=v.entities(dim)[pair[1]]
                        and v.rows['city'][pair[0]]!=v.rows['city'][pair[1]]}
                winner=separated_extreme(scores,smallest=True)
                if winner is None: continue
                text=self.text(v,'Among pairs with different {subject} in {category} and different towns, which pair’s towns are closest by air?',
                               'מבין הזוגות עם {subject} שונים שמזוהים עם {category} ועם יישובים שונים, של מי היישובים הכי קרובים בקו אווירי?',
                               subject=v.subject(dim),category=v.label(cat))
                explanation=self.discovery(v,dim,cat,winner)+' '+distance_explanation(self,v,winner)
                yield from self.make(v,rng,text,v.pair_name(winner),[v.pair_name(p) for p in scores],(dim,'place.district'),explanation,key=(dim,cat),focus=winner)


class DistrictActivityDiversityRule(SemanticRule):
    rule_id = 'district_activity_diversity'
    difficulty = Difficulty.HARD
    hops = 4

    def candidates(self,v,rng):
        if not v.complete('place.district','hobby.family'): return
        groups=v.groups('place.district')
        counts={district:len(set().union(*(v.memberships['hobby.family'][p] for p in ps))) for district,ps in groups.items()}
        winner=unique_extreme(counts)
        if winner is None or counts[winner]<2: return
        text=self.text(v,'Which district brings together the widest variety of activity families through the hobbies chosen by its players?',
                       'איזה מחוז מביא לקבוצה את המגוון הגדול ביותר של משפחות תחביבים, לפי הבחירות של המשתתפים שגרים בו?')
        families=sorted(set().union(*(v.memberships['hobby.family'][p] for p in groups[winner])))
        explanation=self.text(v,'Players from {district} chose hobbies spanning {families}.',
                              'המשתתפים מ{district} בחרו תחביבים שכוללים {families}.',district=v.label(winner),families=', '.join(v.label(c) for c in families))
        yield from self.make(v,rng,text,v.label(winner),[v.label(c) for c in counts],('place.district','hobby.family'),explanation,key=('district_hobbies',))


def semantic_rules(knowledge):
    return tuple(rule(knowledge) for rule in (
        SemanticCountRule,SemanticSubsetCountRule,SemanticScopedPairRule,SemanticModeRule,SemanticRareRule,SemanticDiversityRule,
        SemanticDifferentPairRule,SemanticIntersectionRule,SemanticFilteredModeRule,
        SemanticOutlierRule,MusicArtistBridgeRule,LocalityExtremeRule,LocalityDistanceRule,
        LocalityNearestRule,LocalityMiddleRule,LocalityDistinctRule,SemanticNearbyPairRule,
        DistrictActivityDiversityRule,
    ))
