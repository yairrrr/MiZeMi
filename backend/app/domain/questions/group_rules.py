"""Previous group-first families, plus the production wrapper for simple social questions.

The group families below required complete consented knowledge for a dimension,
which realistic rooms rarely have; production now uses the category-first
families in ``discovery_rules.py`` (see QUESTION_ENGINE_DIAGNOSTIC.md). They stay
as a regression-tested catalog. ``SocialLegacyRule`` remains the production
wrapper for literal social questions.
"""
from dataclasses import replace
from itertools import combinations, islice

from app.domain.questions.advanced_rules import unique_extreme
from app.domain.questions.language import normalize, say
from app.domain.questions.question import Difficulty
from app.domain.questions.semantic import DIMENSIONS
from app.domain.questions.semantic_rules import (
    SemanticRule, LocalityDistanceRule, LocalityExtremeRule, LocalityDistinctRule,
    separated_extreme,
)
from app.domain.questions.semantic_distractors import category_choices

TASTE_DIMS = ('movie.genre', 'hobby.family', 'food.cuisine', 'food.format', 'music.genre', 'artist.genre', 'song.genre')
COUNT_DIMS = ('hobby.physical', 'hobby.setting', *TASTE_DIMS)
FACT_DIM = {'artist.genre': 'music.genre', 'song.genre': 'music.genre'}

# Named broad families avoid asking about arbitrary overlapping taxonomy levels.
HOBBY_FAMILIES = frozenset(('hobby.sport', 'hobby.creative', 'hobby.digital',
                          'hobby.table_games', 'hobby.nature', 'hobby.learning', 'hobby.cooking',
                          'hobby.collecting', 'hobby.wellbeing', 'hobby.social', 'hobby.travel'))


class GroupRule(SemanticRule):
    mix = 'semantic'
    person_answer = False

    def make(self, *args, **kwargs):
        for q in super().make(*args, **kwargs):
            signature = ('membership', *q.semantic_key[1:]) if self.rule_id in ('group_count', 'group_unique') else q.semantic_key
            metadata=(*q.metadata, ('mix', self.mix), ('person_answer', self.person_answer))
            if self.rule_id in ('group_count','group_unique'):
                dim,cat=q.semantic_key[1:]
                people=tuple(args[0].groups(dim)[cat])
                metadata+= (('membership_signature',(q.source_field_keys[0],*people)),)
            yield replace(q, semantic_key=signature, metadata=metadata)

    def groups(self, v, dim, people=None):
        groups = v.groups(dim, people)
        if dim == 'hobby.family':
            groups = {c: p for c, p in groups.items() if c in HOBBY_FAMILIES}
        return groups

    def choices(self, v, dim, winner, represented=()):
        choices=category_choices(self.knowledge, FACT_DIM.get(dim, dim), winner, represented)
        if dim=='hobby.family':
            # A parent and its child cannot be competing broad-family answers.
            choices=list(dict.fromkeys((*choices,*represented,*sorted(HOBBY_FAMILIES))))
            choices=[c for c in choices if c in HOBBY_FAMILIES and c in self.knowledge.categories][:4]
        return [v.label(c) for c in choices]

    def clue(self, v, dim, cat, *, single=False):
        en, he = {
            'movie.genre': ('{c} movies', 'סרטים בז׳אנר {c}'),
            'hobby.family': ('hobbies related to {c}', 'תחביבים שקשורים ל{c}'),
            'food.cuisine': ('foods associated with {c}', 'מאכלים שמזוהים עם {c}'),
            'food.format': ('foods from the {c} family', 'מאכלים ממשפחת {c}'),
            'music.genre': ('{c} music', 'מוזיקה בסגנון {c}'),
            'artist.genre': ('artists associated with {c}', 'אמנים שמזוהים עם {c}'),
            'song.genre': ('{c} songs', 'שירים בסגנון {c}'),
            'place.region': ('towns in {c}', 'יישובים ב{c}'),
            'hobby.setting': ('hobbies usually done {c}', 'תחביבים שעושים בדרך כלל {c}'),
            'hobby.physical': ('hobbies involving {c}', 'תחביבים שכוללים {c}'),
        }[dim]
        label=v.label(cat)
        if dim=='place.region' and v.dataset.language=='he' and label.startswith('ה'): label=label[1:]
        clue=self.text(v, en, he, c=label)
        if single:
            replacements=(('סרטים בז׳אנר','סרט בז׳אנר'),('תחביבים שקשורים','תחביב שקשור'),
                          ('מאכלים שמזוהים','מאכל שמזוהה'),('מאכלים ממשפחת','מאכל ממשפחת'),
                          ('אמנים שמזוהים','אמן שמזוהה'),('שירים בסגנון','שיר בסגנון'),
                          ('תחביבים שעושים','תחביב שעושים'),('תחביבים שכוללים','תחביב שכולל'),
                          ('hobbies related','a hobby related'),
                          ('foods associated','a food associated'),('foods from','a food from'),
                          ('artists associated','an artist associated'),('songs in','a song in'),
                          ('hobbies usually','a hobby usually'),('hobbies involving','a hobby involving'))
            for plural,singular in replacements: clue=clue.replace(plural,singular)
            if v.dataset.language=='en' and dim in ('movie.genre','song.genre'):
                article='an' if label[0].lower() in 'aeiou' else 'a'
                clue=f'{article} {label} '+('movie' if dim=='movie.genre' else 'song')
        return clue

    def mode_text(self, v, dim):
        en, he = {
            'movie.genre': ('Which film genre appears in the most people’s choices?', 'לפי הסרטים שבחרתם, איזה ז׳אנר מופיע אצל הכי הרבה אנשים?'),
            'hobby.family': ('Which activity family is most common in our group?', 'לפי התחביבים שבחרתם, איזה תחום הכי נפוץ בקבוצה?'),
            'food.cuisine': ('Which cuisine is most popular in our group’s food choices?', 'לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה?'),
            'food.format': ('Which food family is most common in our group?', 'איזו משפחת מאכלים הכי נפוצה בקבוצה?'),
            'music.genre': ('Which music style is most common in our group?', 'איזה סגנון מוזיקה הכי נפוץ בקבוצה?'),
            'artist.genre': ('Looking at our chosen artists, which music style is most common?', 'לפי האמנים שבחרתם, איזה סגנון מוזיקה הכי נפוץ בקבוצה?'),
            'song.genre': ('Looking at our chosen songs, which music style is most common?', 'לפי השירים שבחרתם, איזה סגנון מוזיקה הכי נפוץ בקבוצה?'),
            'place.region': ('Which region is home to the most people in our group?', 'מאיזה אזור בארץ מגיעים הכי הרבה אנשים בקבוצה?'),
        }[dim]
        return self.text(v, en, he)

    def discovery(self, v, dim, cat, people):
        works=v.evidence(dim, cat, people)
        single=len(people)==1
        text=self.text(v, 'One person chose {clue}: {works}.' if single else '{n} people chose {clue}: {works}.',
                       'אדם אחד בחר {clue}: {works}.' if single else '{n} אנשים בחרו {clue}: {works}.',
                       clue=self.clue(v,dim,cat,single=single),works=works,n=len(people))
        if dim=='place.region':
            text=self.text(v,'One person is from {category}: {works}.' if single else '{n} people are from {category}: {works}.',
                           'אדם אחד מגיע מ{category}: {works}.' if single else '{n} אנשים מגיעים מ{category}: {works}.',
                           category=v.label(cat),works=works,n=len(people))
        if dim == 'hobby.setting':
            text += self.text(v, ' This describes the usual setting of the activity, not where anyone actually does it.',
                              ' סופרים לפי מקום הפעילות המקובל של התחביב, לא לפי המקום שבו כל אחד עושה אותו בפועל.')
        return text


class GroupCountRule(GroupRule):
    rule_id='group_count'
    difficulty=Difficulty.EASY
    mix='simple'

    def candidates(self, v, rng):
        for dim in COUNT_DIMS:
            if not v.complete(dim): continue
            for cat, people in self.groups(v, dim).items():
                if not 0 < len(people) < len(v.ids): continue
                if dim=='hobby.physical' and cat!='activity.physical': continue
                if dim=='hobby.setting' and cat=='setting.flexible': continue
                text=self.text(v, 'How many people in our group chose {clue}?',
                               'כמה אנשים בקבוצה בחרו {clue}?', clue=self.clue(v, dim, cat))
                yield from self.number(v, rng, text, len(people), len(v.ids), (dim,),
                                       self.discovery(v, dim, cat, people), key=(dim, cat))


class GroupScopedCountRule(GroupCountRule):
    rule_id='group_scoped_count'

    def candidates(self, v, rng):
        for dim in TASTE_DIMS:
            if v.complete(dim): continue
            people=tuple(p for p in v.ids if p in v.memberships[dim])[:6]
            if len(people)<3: continue
            for cat, holders in self.groups(v, dim, people).items():
                if not 0<len(holders)<len(people): continue
                text=self.text(v, 'Among {names}, how many chose {clue}?',
                               'מבין {names}, כמה בחרו {clue}?',
                               names=', '.join(v.name(p) for p in people), clue=self.clue(v,dim,cat))
                yield from self.number(v,rng,text,len(holders),len(people),(dim,),
                    self.discovery(v,dim,cat,holders),key=(dim,cat,*people),people=people)


class GroupModeRule(GroupRule):
    rule_id='group_mode'
    difficulty=Difficulty.EASY

    def candidates(self,v,rng):
        for dim in TASTE_DIMS:
            if not v.complete(dim): continue
            groups=self.groups(v,dim); counts={c:len(p) for c,p in groups.items()}
            winner=next(iter(counts)) if len(counts)==1 else unique_extreme(counts)
            if winner is None or counts[winner]<2: continue
            yield from self.make(v,rng,self.mode_text(v,dim),v.label(winner),self.choices(v,dim,winner,groups),
                (dim,),self.discovery(v,dim,winner,groups[winner]),key=(dim,))


class GroupUniqueRule(GroupRule):
    rule_id='group_unique'
    difficulty=Difficulty.EASY
    mix='simple'
    person_answer=True

    def candidates(self,v,rng):
        for dim in TASTE_DIMS:
            if not v.complete(dim): continue
            for cat,people in self.groups(v,dim).items():
                if len(people)!=1: continue
                p=people[0]
                clue=self.clue(v,dim,cat,single=True)
                text=self.text(v,'Only one person in our group chose {clue}. Who?',
                               'רק אחד בקבוצה בחר {clue}. מי זה?',clue=clue)
                explanation=self.text(v,'{name}: {discovery}','{name}: {discovery}',
                    name=v.name(p),discovery=self.discovery(v,dim,cat,people))
                yield from self.make(v,rng,text,v.name(p),[v.name(i) for i in v.ids],(dim,),
                                     explanation,key=(dim,cat),focus=people)


class GroupComparisonRule(GroupRule):
    rule_id='group_comparison_semantic'

    def candidates(self,v,rng):
        for dim in (*TASTE_DIMS,'hobby.setting','place.region'):
            if not v.complete(dim): continue
            groups=self.groups(v,dim)
            if dim=='hobby.setting':
                groups={c:p for c,p in groups.items() if c in ('setting.outdoor','setting.indoor')}
            for a,b in islice(combinations(groups,2),80):
                if len(groups[a])==len(groups[b]): continue
                winner=a if len(groups[a])>len(groups[b]) else b
                subject={
                    'movie.genre':('film genres','ז׳אנרי הסרטים'), 'hobby.family':('activity families','תחומי התחביבים'),
                    'food.cuisine':('cuisines','המטבחים'), 'food.format':('food families','משפחות המאכלים'), 'music.genre':('music styles','סגנונות המוזיקה'),
                    'artist.genre':('music styles of our chosen artists','סגנונות המוזיקה של האמנים שבחרתם'),
                    'song.genre':('music styles of our chosen songs','סגנונות המוזיקה של השירים שבחרתם'),
                    'hobby.setting':('usual activity settings','מקומות הפעילות הרגילים של התחביבים'),
                    'place.region':('home regions','אזורי המגורים'),
                }[dim]
                text=self.text(v,'Which of these {subject} is more common in our group?',
                               'מה נפוץ יותר בקבוצה מבין {subject} הבאים?',subject=subject[v.dataset.language=='he'])
                if dim=='hobby.setting':
                    text=self.text(v,'What is more common in our group: outdoor hobbies or indoor hobbies?',
                                   'מה נפוץ יותר בקבוצה: תחביבי חוץ או תחביבים במקומות סגורים?')
                if dim in ('artist.genre','song.genre'):
                    subject=self.text(v,'artists' if dim=='artist.genre' else 'songs','האמנים' if dim=='artist.genre' else 'השירים')
                    text=self.text(v,'Looking at our chosen {subject}, which of these two music styles is more common?',
                                   'לפי {subject} שבחרתם, איזה משני סגנונות המוזיקה האלה נפוץ יותר?',subject=subject)
                explanation=self.discovery(v,dim,a,groups[a])+' '+self.discovery(v,dim,b,groups[b])
                yield from self.make(v,rng,text,v.label(winner),[v.label(a),v.label(b)],(dim,),explanation,key=(dim,a,b))


class GroupDiversityRule(GroupRule):
    rule_id='group_diversity'

    def candidates(self,v,rng):
        for dim in (*TASTE_DIMS,'place.region'):
            if not v.complete(dim): continue
            groups=self.groups(v,dim)
            if dim=='music.genre':
                # Count selected styles once, not both a style and its parent.
                choices={e.canonical_id:e for e in v.entities(dim).values()}
                count=len(choices)
                names=', '.join(e.label(v.dataset.language) for e in choices.values())
            else:
                if dim=='food.cuisine' and 'food.asian' in groups:
                    # A broad region cannot stand in for an unknown specific cuisine.
                    if any(v.memberships[dim][p]==frozenset({'food.asian'}) for p in v.ids): continue
                    groups={c:ps for c,ps in groups.items() if c!='food.asian'}
                count=len(groups)
                names=', '.join(v.label(c) for c in groups)
            if not 2<=count<=6: continue  # A short, understandable discovery, not a taxonomy inventory.
            questions={
                'movie.genre': ('How many film genres are represented in our group?', 'כמה ז׳אנרים של סרטים מיוצגים בקבוצה?'),
                'hobby.family': ('How many activity families are represented in our group?', 'כמה תחומים שונים יש בתחביבים של הקבוצה?'),
                'food.cuisine': ('How many cuisines are behind our group’s food choices?', 'כמה מטבחים שונים מסתתרים מאחורי המאכלים שבחרתם?'),
                'food.format': ('How many food families are represented in our group?', 'כמה משפחות של מאכלים מיוצגות בקבוצה?'),
                'music.genre': ('How many music styles are represented in our group?', 'כמה סגנונות מוזיקה מיוצגים בקבוצה?'),
                'artist.genre': ('How many music styles connect the artists we chose?', 'כמה סגנונות מוזיקה יש בין האמנים שבחרתם?'),
                'song.genre': ('How many music styles connect the songs we chose?', 'כמה סגנונות מוזיקה יש בין השירים שבחרתם?'),
                'place.region': ('How many different regions are represented in our group?', 'כמה אזורים בארץ מיוצגים בקבוצה?'),
            }
            text=self.text(v,*questions[dim])
            explanation=self.text(v,'{n} families: {names}. A choice can belong to more than one family.',
                                  '{n} תחומים: {names}. בחירה אחת יכולה להשתייך ליותר מתחום אחד.',
                                  n=count,names=names)
            if dim=='music.genre':
                explanation=self.text(v,'{n} chosen styles: {names}. Alternate spellings count once.',
                                      '{n} סגנונות שנבחרו: {names}. כתיבים שונים של אותו סגנון נספרים פעם אחת.',n=count,names=names)
            yield from self.number(v,rng,text,count,max(count+2,len(v.ids)),(dim,),explanation,key=(dim,))


class GroupDifferentPairRule(GroupRule):
    rule_id='group_different_pair'
    person_answer=True

    def candidates(self,v,rng):
        for dim in ('hobby.family','food.cuisine'):
            if not v.complete(dim): continue
            for cat,people in self.groups(v,dim).items():
                if len(people)!=2 or v.entities(dim)[people[0]]==v.entities(dim)[people[1]]: continue
                text=self.text(v,'Which two people chose different {subject}, both in {category}?',
                               'איזה שני אנשים בחרו {subject} שונים שמתחברים דרך {category}?',
                               subject=v.subject(dim),category=v.label(cat))
                yield from self.make(v,rng,text,v.pair_name(people),[v.pair_name(p) for p in combinations(v.ids,2)],
                    (dim,),self.discovery(v,dim,cat,people),key=(dim,cat),focus=people)


class RegionMajorityRule(GroupRule):
    rule_id='region_majority'
    difficulty=Difficulty.EASY
    mix='geographic'

    def candidates(self,v,rng):
        dim='place.region'
        if not v.complete(dim): return
        groups=v.groups(dim); counts={c:len(p) for c,p in groups.items()}
        winner=next(iter(counts)) if len(counts)==1 else unique_extreme(counts)
        if winner is None: return
        # A plurality is not a majority. Use "most" unless strictly over half.
        text=self.mode_text(v,dim)
        if counts[winner]*2>len(v.ids):
            text=self.text(v,'Which region is home to the majority of our group?',
                           'מאיזה אזור בארץ מגיע רוב הקבוצה?')
        yield from self.make(v,rng,text,v.label(winner),self.choices(v,dim,winner,groups),(dim,),
                             self.discovery(v,dim,winner,groups[winner]),key=(dim,))


class RegionUniqueRule(GroupRule):
    rule_id='region_unique'
    difficulty=Difficulty.EASY
    mix='geographic'
    person_answer=True

    def candidates(self,v,rng):
        dim='place.region'
        if not v.complete(dim): return
        groups=v.groups(dim); singletons=[ps[0] for ps in groups.values() if len(ps)==1]
        if len(singletons)!=1: return
        p=singletons[0]; cat=next(iter(v.memberships[dim][p]))
        text=self.text(v,'Who is the only person from a region nobody else in our group comes from?',
                       'מי היחיד בקבוצה שמגיע מאזור שאף אחד אחר לא מגיע ממנו?')
        yield from self.make(v,rng,text,v.name(p),[v.name(i) for i in v.ids],(dim,),
            self.text(v,'{name}: {evidence}','{name}: {evidence}',name=v.name(p),evidence=self.discovery(v,dim,cat,[p])),key=(dim,),focus=(p,))


class GeographicOutlierRule(GroupRule):
    rule_id='geographic_outlier'
    mix='geographic'
    person_answer=True
    hops=3

    def candidates(self,v,rng):
        if not v.distances: return
        scores={p:sum(d for pair,d in v.distances.items() if p in pair)/(len(v.ids)-1) for p in v.ids}
        winner=separated_extreme(scores,margin=1.0)
        if winner is None: return
        text=self.text(v,'Who lives furthest from the rest of our group, on average?',
                       'מי גר הכי רחוק משאר הקבוצה, בממוצע?')
        explanation=self.text(v,'{name}, from {town}: an average of about {km} km to the other towns, by air.',
                              '{name}, מ{town}: בממוצע כ־{km} ק״מ בקו אווירי לשאר היישובים בקבוצה.',
                              name=v.name(winner),town=v.rows['city'][winner].label(v.dataset.language),km=round(scores[winner]))
        yield from self.make(v,rng,text,v.name(winner),[v.name(p) for p in v.ids],('place.region',),explanation,key=('average_distance',),focus=(winner,))


class GroupFilteredModeRule(GroupRule):
    rule_id='group_filtered_mode'
    difficulty=Difficulty.HARD
    mix='geographic'
    hops=4

    def candidates(self,v,rng):
        for condition,target in (('movie.genre','hobby.family'),('hobby.family','movie.genre'),
                                 ('food.cuisine','place.region'),('place.region','food.cuisine'),
                                 ('music.genre','hobby.family'),('hobby.family','music.genre')):
            if not v.complete(condition): continue
            for cat,people in self.groups(v,condition).items():
                if not 3<=len(people)<len(v.ids): continue
                if any(p not in v.memberships[target] for p in people): continue
                groups=self.groups(v,target,people); counts={c:len(ps) for c,ps in groups.items()}
                winner=next(iter(counts)) if len(counts)==1 else unique_extreme(counts)
                if winner is None or counts[winner]<2: continue
                text=self.text(v,'Among people who chose {clue}, which {dimension} is most common?',
                               'מבין מי שבחרו {clue}, מה נפוץ ביותר מבין {dimension} הבאים?',
                               clue=self.clue(v,condition,cat),dimension=v.dimension_label(target))
                if v.dataset.language=='en':
                    target_text={'movie.genre':'film genre','hobby.family':'activity family',
                                 'food.cuisine':'cuisine','music.genre':'music style','place.region':'region'}[target]
                    prefix=('Among people from '+v.label(cat) if condition=='place.region'
                            else 'Among people who chose '+self.clue(v,condition,cat))
                    text=prefix+', which '+target_text+' is most common?'
                if v.dataset.language=='he':
                    target_text={'movie.genre':'איזה ז׳אנר קולנוע הכי נפוץ',
                                 'hobby.family':'איזה תחום תחביבים הכי נפוץ',
                                 'food.cuisine':'איזה מטבח הכי נפוץ',
                                 'music.genre':'איזה סגנון מוזיקה הכי נפוץ',
                                 'place.region':'מאיזה אזור בארץ מגיעים הכי הרבה אנשים'}[target]
                    prefix=('מבין המשתתפים שמגיעים מ'+v.label(cat) if condition=='place.region'
                            else 'מבין מי שבחרו '+self.clue(v,condition,cat))
                    text=prefix+', '+target_text+'?'
                explanation=self.discovery(v,condition,cat,people)+' '+self.discovery(v,target,winner,groups[winner])
                yield from self.make(v,rng,text,v.label(winner),self.choices(v,target,winner,groups),(condition,target),
                                     explanation,key=(condition,cat,target),people=people)


class GroupIntersectionCountRule(GroupRule):
    rule_id='group_intersection_count'
    difficulty=Difficulty.HARD
    mix='geographic'
    hops=3

    def candidates(self,v,rng):
        for a,b in (('movie.genre','hobby.family'),('food.cuisine','hobby.family'),('music.genre','food.cuisine')):
            if not v.complete(a,b): continue
            ga,gb=self.groups(v,a),self.groups(v,b)
            for ca,cb in islice(((ca,cb) for ca in ga for cb in gb),80):
                if len(ga[ca])<2 or len(gb[cb])<2: continue
                both=tuple(p for p in ga[ca] if p in gb[cb])
                if not 0<len(both)<min(len(ga[ca]),len(gb[cb])): continue
                text=self.text(v,'How many people chose both {first} and {second}?',
                               'כמה אנשים בחרו גם {first} וגם {second}?',
                               first=self.clue(v,a,ca),second=self.clue(v,b,cb))
                explanation=self.discovery(v,a,ca,both)+' '+self.discovery(v,b,cb,both)
                yield from self.number(v,rng,text,len(both),len(v.ids),(a,b),explanation,key=(a,ca,b,cb))


class RegionHobbyDiversityRule(GroupRule):
    rule_id='region_hobby_diversity'
    difficulty=Difficulty.HARD
    mix='geographic'
    hops=4

    def candidates(self,v,rng):
        if not v.complete('place.region','hobby.family'): return
        groups=v.groups('place.region')
        if len(groups)<2: return
        families={r:set(self.groups(v,'hobby.family',ps)) for r,ps in groups.items()}
        winner=unique_extreme({r:len(fs) for r,fs in families.items()})
        if winner is None or len(groups[winner])<2 or len(families[winner])<2: return
        text=self.text(v,'Which region brings the widest range of hobbies to our group?',
                       'מאיזה אזור מגיע המגוון הכי רחב של תחומי תחביבים בקבוצה?')
        explanation=self.text(v,'People from {region} chose hobbies in {families}.',
                              'המשתתפים מ{region} בחרו תחביבים בתחומים {families}.',
                              region=v.label(winner),families=', '.join(v.label(c) for c in sorted(families[winner])))
        yield from self.make(v,rng,text,v.label(winner),[v.label(c) for c in groups],
            ('place.region','hobby.family'),explanation,key=('region_hobbies',))


class SocialGeographyRule:
    """Reuse proven coordinate rules, with explicit social selection metadata."""
    def __init__(self,rule): self.rule=rule; self.rule_id=rule.rule_id
    def generate(self,dataset,rng):
        for q in self.rule.generate(dataset,rng):
            difficulty=Difficulty.MEDIUM if self.rule_id=='locality_distance_pair' else q.difficulty
            yield replace(q,difficulty=difficulty,metadata=(*q.metadata,('mix','geographic'),
                ('person_answer',self.rule_id!='locality_distinct')))


def group_rules(knowledge):
    rules=tuple(cls(knowledge) for cls in (
        GroupCountRule,GroupScopedCountRule,GroupModeRule,GroupUniqueRule,GroupComparisonRule,
        GroupDiversityRule,GroupDifferentPairRule,RegionMajorityRule,RegionUniqueRule,
        GeographicOutlierRule,GroupFilteredModeRule,GroupIntersectionCountRule,RegionHobbyDiversityRule,
    ))
    return (*rules,*(SocialGeographyRule(cls(knowledge)) for cls in
                    (LocalityDistanceRule,LocalityExtremeRule,LocalityDistinctRule)))


# The reasoning each raw-answer family performs, in the same terms the
# discovery families use, so the selector compares like with like.
DIRECT_OPERATIONS = {'unique_value': 'unique', 'value_count': 'count', 'most_common_value': 'majority',
                     'group_comparison': 'comparison', 'age_ranking': 'extreme'}
DIRECT_FAMILIES = {'unique_value': 'DIRECT_UNIQUE', 'most_common_value': 'DIRECT_MAJORITY', 'value_count': 'DIRECT_COUNT',
                   'group_comparison': 'DIRECT_COMPARISON', 'age_ranking': 'DIRECT_AGE'}
FIELD_DOMAINS = {'city': 'place', 'favorite_food': 'food', 'hobby': 'hobby', 'favorite_movie': 'movie',
                 'favorite_music': 'music', 'favorite_artist': 'music', 'favorite_song': 'music', 'age': 'age',
                 'personal_fact': 'social'}


def raw_disclosure(rule_id, q, dataset):
    """What a raw-answer question settles, in the selector's ``reveals``/``needs`` terms (discovery_rules.py).

    These questions have no explanation, so only the answer itself is disclosed:
    "what is the most common food?" (pizza) settles "pizza or sushi?".
    """
    field = q.source_field_keys[0]
    value_of = {pid: str(normalize(value)) for pid, value in dataset.values_for(field)}
    values = tuple(dict.fromkeys(value_of[p] for p in q.involved_player_ids if p in value_of))
    if rule_id == 'value_count' and len(values) == 1:
        majority = 2 * len(q.involved_player_ids) >= len(value_of)  # Tied races are never asked.
        return ((('count', field, values[0]), *((('rank', field, values[0]),) if majority else ())),
                ((('count', field, values[0]),),))
    if rule_id == 'most_common_value' and len(values) == 1:
        return ((('rank', field, values[0]),), ((('rank', field, values[0]),),))
    if rule_id == 'group_comparison' and len(values) == 2:
        a, b = values
        return ((), ((('rank', field, a),), (('rank', field, b),), (('count', field, a), ('count', field, b))))
    return (), ()


class SocialLegacyRule:
    """Simple social questions about literal answers ("who is the only one who chose couscous?").

    Production keeps these as the direct share of a group-first game. Group
    facts about music choices come from the music families instead, which
    also render the fixed English choice values in the game language.
    """
    def __init__(self,rule,knowledge): self.rule=rule; self.rule_id=rule.rule_id; self.knowledge=knowledge
    def generate(self,dataset,rng):
        from app.domain.questions.semantic import enrich
        alias_collisions=enrich(dataset,self.knowledge).raw_alias_collisions
        person=self.rule_id in ('unique_value','age_ranking')
        for q in self.rule.generate(dataset,rng):
            if alias_collisions.intersection(q.source_field_keys): continue
            if self.rule_id in ('value_count','unique_value') and 'age' in q.source_field_keys:
                continue
            if 'favorite_music' in q.source_field_keys:
                continue
            if 'personal_fact' in q.source_field_keys and self.rule_id!='unique_value':
                continue
            if self.rule_id=='value_count' and len(q.involved_player_ids)==1:
                continue  # "How many live in Herzliya?" (1) only restates who is unique.
            if (self.rule_id=='value_count'
                    and len(q.involved_player_ids)==len(dataset.values_for(q.source_field_keys[0]))):
                continue  # "How many chose pizza?" when everyone did is not a question.
            # Do not pretend an unshared raw answer is a different answer.
            if any(len(dataset.values_for(f)) != dataset.player_count for f in q.source_field_keys):
                continue
            if q.source_field_keys==('personal_fact',):
                value=dict(dataset.values_for('personal_fact'))[q.involved_player_ids[0]]
                q=replace(q,text=say(dataset.language,'Who wrote this about themselves: "{value}"?',
                                     'מי כתב/ה את זה על עצמו/ה: "{value}"?',value=value))
            field=q.source_field_keys[0]
            operation=DIRECT_OPERATIONS[self.rule_id]
            fact=q.semantic_key or (q.source_rule_id,*q.source_field_keys,*q.involved_player_ids[:1])
            metadata=(*q.metadata,('mix','simple'),('person_answer',person),('kind','direct'),
                ('family',DIRECT_FAMILIES[self.rule_id]),('domain',FIELD_DOMAINS.get(field,'social')),
                ('reasoning_hops',1),('operation',operation),('topic',field),
                ('signature',(operation,field,*map(str,fact))))
            if self.rule_id in ('unique_value','value_count','most_common_value'):
                # "Who is the only one in Rehovot?" and "how many live in Rehovot?" (1) are one fact.
                holders=q.involved_player_ids[:1] if self.rule_id=='unique_value' else q.involved_player_ids
                metadata+=(('membership_signature',(q.source_field_keys[0],tuple(holders))),)
            reveals,needs=raw_disclosure(self.rule_id,q,dataset)
            if reveals or needs:
                metadata+=(('reveals',reveals),('needs',needs))
            yield replace(q,metadata=metadata)


def social_legacy_rules(rules,knowledge):
    return tuple(SocialLegacyRule(r,knowledge) for r in rules if r.rule_id in DIRECT_FAMILIES)
