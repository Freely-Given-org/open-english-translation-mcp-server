"""Regression scenarios for evidence an LLM uses to answer research questions."""
import pytest
from oet_mcp_server.database import OETDatabase


@pytest.fixture
def db():
    return OETDatabase()


def test_john_interlinear_does_not_insert_unused_article(db):
    selected = db.get_passage('John 1:1', version='interlinear').verses[0].words
    all_words = db.get_passage('John 1:1', version='interlinear', include_variants=True).verses[0].words
    assert len(selected) == 17
    assert len(all_words) == 18
    assert 'JHN_1:1w14' not in {w.ref for w in selected}
    assert db.lookup_word('JHN_1:1w14')['is_selected'] is False


def test_logos_count_excludes_unused_variants(db):
    entry = db.get_lexicon_entry('G3056')
    assert entry.lemma == 'logos'
    assert entry.total_occurrences == 331
    assert entry.unused_variant_occurrences == 54
    assert sum(entry.gloss_distribution.values()) == entry.total_occurrences
    assert db.search_lemma('G30560')['total_matches'] == 331
    assert db.search_lemma('logos', include_variants=True)['total_matches'] == 385


def test_hebrew_stem_search_includes_prefixed_words(db):
    result = db.search_lemma('H7225', limit=100, sampling='canonical')
    assert result['total_matches'] == 51
    assert result['occurrences'][0]['word_link_id'] == 'GEN_1:1w1'
    word = db.lookup_word('GEN_1:1w1')
    assert word['strongs_standard'] == ['H7225']
    assert word['lemmas'][1]['lemma'] == 'רֵאשִׁית'
    assert db.get_lexicon_entry('רֵאשִׁית').total_occurrences == 51


def test_lemma_search_accepts_accent_variants_and_enforces_language(db):
    assert db.search_lemma('agape')['total_matches'] > 100
    assert db.get_lexicon_entry('λόγος', lang='hebrew') is None
    assert db.get_lexicon_entry('message', lang='hebrew') is None


@pytest.mark.parametrize('ref', ['John 1:999', 'John 1:1-999', 'John 1:5-3', 'John 0:1', 'John 99', 'John 1-99'])
def test_invalid_reference_never_substitutes_a_chapter(db, ref):
    with pytest.raises(ValueError):
        db.get_passage(ref)


@pytest.mark.parametrize('ref,code', [('1Cor 13:4', 'CO1'), ('Song of Songs 1:1', 'SNG'), ('Song of Solomon 1:1', 'SNG')])
def test_multiword_and_compact_references(db, ref, code):
    assert db.get_passage(ref).book_code == code


def test_search_filters_matching_version_and_handles_punctuation(db):
    assert db.search_text('DOM', version='rv') == []
    assert db.search_text('DOM', version='lv')
    db.search_text("God's love")
    with pytest.raises(ValueError):
        db.search_text('')


def test_translation_decisions_keep_their_source(db):
    verse = db.get_passage('John 1:1').verses[0]
    assert any(d.source_version == 'LV' and d.code == '+' for d in verse.decisions)
    comparison = db.compare_passage('John 1:1')[0]
    assert all(d.source_version == 'RV' for d in comparison.translation_decisions_rv)
    assert not any(d.code == '+' for d in comparison.translation_decisions_rv)


def test_representative_search_and_complete_paging(db):
    sample = db.search_lemma('logos')
    assert len({x['ref'].split()[0] for x in sample['occurrences']}) > 5
    first = db.search_lemma('logos', book='John', limit=2, sampling='canonical')
    second = db.search_lemma('logos', book='John', limit=2, sampling='canonical', offset=first['next_offset'])
    assert not ({r['word_link_id'] for r in first['occurrences']} & {r['word_link_id'] for r in second['occurrences']})
    assert all(r['ref'].startswith('JHN ') for r in second['occurrences'])
    assert first['total_matches'] == second['total_matches']


def test_footnote_without_ft_is_recovered(db):
    notes = db.get_passage('1 Esdras 2:16').verses[0].notes
    assert any('Rehum' in n.content for n in notes)
    assert any('Shimshai' in n.content for n in notes)
    assert all('\\' not in n.content for n in notes)


def test_poetry_and_editorial_context_are_available(db):
    verse = db.get_passage('Psalm 1:1', include_structure=True).verses[0]
    assert len(verse.structure['RV']) == 4
    assert verse.structure['RV'][0]['marker'] == 'p'  # Preserve the source's initial paragraph.
    assert all(s['marker'] == 'q2' for s in verse.structure['RV'][1:])
    assert verse.structure['RV'][0]['section_id'] == 'PSA.RV.S1'
    assert not db.get_passage('Acts 1:23').verses[0].has_poetry_parallel
    section = db.get_section('PSA.RV.S1')
    assert section.verses[0].verse_id == 'PSA.1.1'
    context = db.get_book_context('Tobit')
    assert 'WEBBE' in ' '.join(context['sources']['RV']['source_notes'])
    assert context['sources']['RV']['introduction']
    assert 'LV' not in context['sources']


def test_alignment_links_and_offsets_are_source_backed(db):
    verse = db.get_passage('John 1:1', include_alignment=True, include_raw=True).verses[0]
    messages = [a for a in verse.alignments if a['text'] == 'message']
    assert messages
    assert any(a['word_link_id'] == 'JHN_1:1w5' for a in messages)
    assert all('add*' not in a['text'] for a in verse.alignments)
    assert any(a['text'] == 'beginning' for a in verse.alignments)
    for alignment in verse.alignments:
        raw = verse.rv_esfm if alignment['source_version'] == 'RV' else verse.lv_esfm
        assert f"¦{alignment['word_num']}" in raw[alignment['source_start']:alignment['source_end']]
        word = db.lookup_word(alignment['word_link_id'])
        assert word['word_num'] == alignment['word_num']
    assert db.lookup_word('NT:62342')['word_link_id'] == 'JHN_1:1w5'


def test_grammar_is_decoded_with_the_source_scheme(db):
    greek = db.lookup_word('JHN_1:1w3')['grammar']
    assert greek['scheme'] == 'SR-GNT'
    assert greek['components'][0]['tense'] == 'imperfect'
    hebrew = db.lookup_word('GEN_1:1w2')['grammar']
    assert hebrew['scheme'] == 'OSHB'
    assert hebrew['components'][0]['stem'] == 'qal'
    assert hebrew['components'][0]['number'] == 'singular'
    assert db.lookup_word('DAN_2:5w1')['lang'] == 'aramaic'


def test_paging_does_not_skip_or_duplicate_verses(db):
    a = db.get_passage('John 1', limit=20)
    b = db.get_passage('John 1', limit=20, offset=a.next_offset)
    c = db.get_passage('John 1', limit=20, offset=b.next_offset)
    ids = [v.verse_id for page in (a,b,c) for v in page.verses]
    assert len(ids) == len(set(ids)) == a.total_verses == 51
    assert c.next_offset is None
    assert len(a.provenance['source_commit']) == 40


def test_grouped_verse_is_retrievable_from_within_its_range(db):
    passage = db.get_passage('1 John 1:2')
    assert any(v.verse_label == '1-3' and v.rv_text for v in passage.verses)
    assert all(v.verse <= 2 for v in passage.verses)


def test_gloss_totals_label_unglossed_source_occurrences(db):
    entry = db.get_lexicon_entry('H7225')
    assert sum(entry.gloss_distribution.values()) + entry.unglossed_occurrences == entry.total_occurrences
