"""Decode documented morphology; retain unknown codes instead of guessing.

Greek: SR-GNT positional codes used by OET's word-page exporter.
Hebrew/Aramaic: https://hb.openscriptures.org/parsing/HebrewMorphologyCodes.html
"""

GREEK_ROLES = dict(N='noun', S='substantive adjective', A='adjective', E='determiner',
                   R='pronoun', V='verb', I='interjection', P='preposition', D='adverb',
                   C='conjunction', T='particle')
GREEK_FIELDS = [
    ('mood', dict(I='indicative', M='imperative', S='subjunctive', O='optative', N='infinitive', P='participle')),
    ('tense', dict(P='present', I='imperfect', F='future', A='aorist', E='perfect', L='pluperfect')),
    ('voice', dict(A='active', M='middle', P='passive')),
    ('person', {'1': 'first', '2': 'second', '3': 'third'}),
    ('case', dict(N='nominative', G='genitive', D='dative', A='accusative', V='vocative')),
    ('gender', dict(M='masculine', F='feminine', N='neuter')),
    ('number', dict(S='singular', P='plural')),
]
HEBREW_ROLES = dict(A='adjective', C='conjunction', D='adverb', N='noun', P='pronoun',
                    R='preposition', S='suffix', T='particle', V='verb')
TYPES = {
    'A': dict(a='adjective', c='cardinal number', g='gentilic', o='ordinal number'),
    'N': dict(c='common', g='gentilic', p='proper name'),
    'P': dict(d='demonstrative', f='indefinite', i='interrogative', p='personal', r='relative'),
    'R': dict(d='definite article'),
    'S': dict(d='directional he', h='paragogic he', n='paragogic nun', p='pronominal'),
    'T': dict(a='affirmation', d='definite article', e='exhortation', i='interrogative',
              j='interjection', m='demonstrative', n='negative', o='direct object marker', r='relative'),
}
HEBREW_STEMS = dict(q='qal', N='niphal', p='piel', P='pual', h='hiphil', H='hophal', t='hithpael',
                    o='polel', O='polal', r='hithpolel', m='poel', M='poal', k='palel', K='pulal',
                    Q='qal passive', l='pilpel', L='polpal', f='hithpalpel', D='nithpael', j='pealal',
                    i='pilel', u='hothpaal', c='tiphil', v='hishtaphel', w='nithpalel', y='nithpoel', z='hithpoel')
ARAMAIC_STEMS = dict(q='peal', Q='peil', u='hithpeel', p='pael', P='ithpaal', M='hithpaal', a='aphel',
                     h='haphel', s='saphel', e='shaphel', H='hophal', i='ithpeel', t='hishtaphel',
                     v='ishtaphel', w='hithaphel', o='polel', z='ithpoel', r='hithpolel', f='hithpalpel',
                     b='hephal', c='tiphel', m='poel', l='palpel', L='ithpalpel', O='ithpolel', G='ittaphal')
CONJUGATIONS = dict(p='perfect (qatal)', q='sequential perfect (weqatal)', i='imperfect (yiqtol)',
                    w='sequential imperfect (wayyiqtol)', h='cohortative', j='jussive', v='imperative',
                    r='active participle', s='passive participle', a='infinitive absolute', c='infinitive construct')
PERSON = {'1': 'first', '2': 'second', '3': 'third'}
GENDER = dict(b='both', c='common', f='feminine', m='masculine')
NUMBER = dict(d='dual', p='plural', s='singular')
STATE = dict(a='absolute', c='construct', d='determined')


def decode_morphology(code: str, lang: str, role: str = '') -> dict:
    code = code or ''
    result = dict(scheme='SR-GNT' if lang == 'greek' else 'OSHB', raw=code, components=[])
    if lang == 'greek':
        part = {'part_of_speech': GREEK_ROLES.get(role, f'unknown ({role})')}
        if len(code) == 7:
            for char, (name, mapping) in zip(code, GREEK_FIELDS):
                if char != '·':
                    part[name] = mapping.get(char, f'unknown ({char})')
        elif code:
            part['unparsed'] = code
        result['components'].append(part)
        return result
    for component in code.split(','):
        if not component:
            continue
        part = dict(raw=component, part_of_speech=HEBREW_ROLES.get(component[0], 'unknown'))
        remainder = component[1:]
        if component.startswith('V') and len(remainder) >= 2:
            stems = ARAMAIC_STEMS if lang == 'aramaic' else HEBREW_STEMS
            part['stem'] = stems.get(remainder[0], f'unknown ({remainder[0]})')
            part['conjugation'] = CONJUGATIONS.get(remainder[1], f'unknown ({remainder[1]})')
            remainder = remainder[2:]
        elif remainder and component[0] in TYPES:
            part['type'] = TYPES[component[0]].get(remainder[0], f'unknown ({remainder[0]})')
            remainder = remainder[1:]
        for name, mapping in [('person', PERSON), ('gender', GENDER), ('number', NUMBER), ('state', STATE)]:
            if remainder and remainder[0] in mapping:
                part[name] = mapping[remainder[0]]
                remainder = remainder[1:]
        if remainder:
            part['unparsed'] = remainder
        result['components'].append(part)
    return result
