# -*- coding: utf-8 -*-
#
# This file is part of INSPIRE.
# Copyright (C) 2014-2017 CERN.
#
# INSPIRE is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INSPIRE is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with INSPIRE. If not, see <http://www.gnu.org/licenses/>.
#
# In applying this license, CERN does not waive the privileges and immunities
# granted to it by virtue of its status as an Intergovernmental Organization
# or submit itself to any jurisdiction.

"""DoJSON rules for MARC fields in 9xx."""

from __future__ import absolute_import, division, print_function

import re
from functools import partial

from dojson import utils
from idutils import is_arxiv_post_2007

from inspire_schemas.api import ReferenceBuilder, load_schema
from inspire_schemas.utils import build_pubnote
from inspire_utils.helpers import force_list, maybe_int
from inspire_utils.record import get_value

from ..model import hep, hep2marc
from ...utils import force_single_element, get_recid_from_ref, get_record_ref


_COLLECTIONS_MAP = {
    'babar-analysisdocument': 'BABAR Analysis Documents',
    'babar-internal-bais': 'BABAR Internal BAIS',
    'babar-internal-note': 'BABAR Internal Notes',
    'cdf-internal-note': 'CDF Internal Notes',
    'cdf-note': 'CDF Notes',
    'cdshidden': 'CDS Hidden',
    'd0-internal-note': 'D0 Internal Notes',
    'd0-preliminary-note': 'D0 Preliminary Notes',
    'h1-internal-note': 'H1 Internal Notes',
    'h1-preliminary-note': 'H1 Preliminary Notes',
    'halhidden': 'HAL Hidden',
    'hep': 'Literature',
    'hephidden': 'HEP Hidden',
    'hermes-internal-note': 'HERMES Internal Notes',
    'larsoft-internal-note': 'LArSoft Internal Notes',
    'larsoft-note': 'LArSoft Notes',
    'zeus-internal-note': 'ZEUS Internal Notes',
    'zeus-preliminary-note': 'ZEUS Preliminary Notes',
}

_COLLECTIONS_REVERSE_MAP = {
    'BABAR Analysis Documents': 'BABAR-AnalysisDocument',
    'BABAR Internal BAIS': 'BABAR-INTERNAL-BAIS',
    'BABAR Internal Notes': 'BABAR-INTERNAL-NOTE',
    'CDF Internal Notes': 'CDF-INTERNAL-NOTE',
    'CDF Notes': 'CDF-NOTE',
    'CDS Hidden': 'CDShidden',
    'D0 Internal Notes': 'D0-INTERNAL-NOTE',
    'D0 Preliminary Notes': 'D0-PRELIMINARY-NOTE',
    'H1 Internal Notes': 'H1-INTERNAL-NOTE',
    'H1 Preliminary Notes': 'H1-PRELIMINARY-NOTE',
    'HAL Hidden': 'HALhidden',
    'HEP Hidden': 'HEPhidden',
    'HERMES Internal Notes': 'HERMEL-INTERNAL-NOTE',
    'LArSoft Internal Notes': 'LARSOFT-INTERNAL-NOTE',
    'LArSoft Notes': 'LARSOFT-NOTE',
    'Literature': 'HEP',
    'ZEUS Internal Notes': 'ZEUS-INTERNAL-NOTE',
    'ZEUS Preliminary Notes': 'ZEUS-PRELIMINARY-NOTE',
}

DOCUMENT_TYPE_MAP = {
    'activityreport': 'activity report',
    'article': 'article',  # XXX: doesn't actually happen.
    'book': 'book',
    'bookchapter': 'book chapter',
    'conferencepaper': 'conference paper',
    'note': 'note',
    'proceedings': 'proceedings',
    'report': 'report',
    'thesis': 'thesis',
}

DOCUMENT_TYPE_REVERSE_MAP = {
    'activity report': 'ActivityReport',
    'article': None,  # XXX: we want to discard it.
    'book': 'Book',
    'book chapter': 'BookChapter',
    'conference paper': 'ConferencePaper',
    'note': 'Note',
    'proceedings': 'Proceedings',
    'report': 'Report',
    'thesis': 'Thesis',
}

RE_VALID_PUBNOTE = re.compile(".*,.*,.*(,.*)?")


@hep.over('record_affiliations', '^902..')
@utils.for_each_value
def record_affiliations(self, key, value):
    record = get_record_ref(value.get('z'), 'institutions')

    return {
        'curated_relation': record is not None,
        'record': record,
        'value': value.get('a'),
    }


@hep2marc.over('902', '^record_affiliations$')
@utils.for_each_value
def record_affiliations2marc(self, key, value):
    return {'a': value.get('value')}


@hep.over('document_type', '^980..')
def document_type(self, key, value):
    schema = load_schema('hep')
    publication_type_schema = schema['properties']['publication_type']
    valid_publication_types = publication_type_schema['items']['enum']

    document_type = self.get('document_type', [])
    publication_type = self.get('publication_type', [])

    a_values = force_list(value.get('a'))
    for a_value in a_values:
        normalized_a_value = a_value.strip().lower()

        if normalized_a_value == 'arxiv':
            continue  # XXX: ignored.
        elif normalized_a_value == 'citeable':
            self['citeable'] = True
        elif normalized_a_value == 'core':
            self['core'] = True
        elif normalized_a_value == 'noncore':
            self['core'] = False
        elif normalized_a_value == 'published':
            self['refereed'] = True
        elif normalized_a_value == 'withdrawn':
            self['withdrawn'] = True
        elif normalized_a_value in _COLLECTIONS_MAP:
            self.setdefault('_collections', []).append(_COLLECTIONS_MAP[normalized_a_value])
        elif normalized_a_value in DOCUMENT_TYPE_MAP:
            document_type.append(DOCUMENT_TYPE_MAP[normalized_a_value])
        elif normalized_a_value in valid_publication_types:
            publication_type.append(normalized_a_value)

    c_value = force_single_element(value.get('c', ''))
    normalized_c_value = c_value.strip().lower()

    if normalized_c_value == 'deleted':
        self['deleted'] = True

    self['publication_type'] = publication_type
    return document_type


@hep2marc.over('980', '^citeable$')
@utils.for_each_value
def citeable2marc(self, key, value):
    if value:
        return {'a': 'Citeable'}


@hep2marc.over('980', '^core$')
@utils.for_each_value
def core2marc(self, key, value):
    if value:
        return {'a': 'CORE'}

    return {'a': 'NONCORE'}


@hep2marc.over('980', '^deleted$')
@utils.for_each_value
def deleted2marc(self, key, value):
    if value:
        return {'c': 'DELETED'}


@hep2marc.over('980', '^refereed$')
@utils.for_each_value
def referred2marc(self, key, value):
    if value:
        return {'a': 'Published'}


@hep2marc.over('980', '^withdrawn$')
@utils.for_each_value
def withdrawn2marc(self, key, value):
    if value:
        return {'a': 'Withdrawn'}


@hep2marc.over('980', '^_collections$')
@utils.for_each_value
def _collections2marc(self, key, value):
    if value in _COLLECTIONS_REVERSE_MAP:
        return {'a': _COLLECTIONS_REVERSE_MAP[value]}


@hep2marc.over('980', '^document_type$')
@utils.for_each_value
def document_type2marc(self, key, value):
    if value in DOCUMENT_TYPE_REVERSE_MAP and DOCUMENT_TYPE_REVERSE_MAP[value]:
        return {'a': DOCUMENT_TYPE_REVERSE_MAP[value]}


@hep2marc.over('980', '^publication_type$')
@utils.for_each_value
def publication_type2marc(self, key, value):
    return {'a': value}


@hep.over('references', '^999C5')
@utils.for_each_value
def references(self, key, value):
    def _get_reference(value):
        def _set_record(el):
            recid = maybe_int(el)
            record = get_record_ref(recid, 'literature')
            rb.set_record(record)

        rb = ReferenceBuilder()
        mapping = [
            ('0', _set_record),
            ('a', rb.add_uid),
            ('b', rb.add_uid),
            ('c', rb.add_collaboration),
            ('e', partial(rb.add_author, role='ed.')),
            ('h', rb.add_refextract_authors_str),
            ('i', rb.add_uid),
            ('k', rb.set_texkey),
            ('m', rb.add_misc),
            ('o', rb.set_label),
            ('p', rb.set_publisher),
            ('q', rb.add_parent_title),
            ('r', rb.add_report_number),
            ('s', rb.set_pubnote),
            ('t', rb.add_title),
            ('u', rb.add_url),
            ('x', rb.add_raw_reference),
            ('y', rb.set_year),
        ]

        for field, method in mapping:
            for el in force_list(value.get(field)):
                if el:
                    method(el)

        return rb.obj

    return _get_reference(value)


@hep2marc.over('999C5', '^references$')
@utils.for_each_value
def references2marc(self, key, value):
    reference = value['reference']

    pids = force_list(reference.get('persistent_identifiers'))
    a_values = ['doi:' + el for el in force_list(reference.get('dois'))]
    a_values.extend(['hdl:' + el['value'] for el in pids if el.get('schema') == 'HDL'])
    a_values.extend(['urn:' + el['value'] for el in pids if el.get('schema') == 'URN'])

    authors = force_list(reference.get('authors'))
    e_values = [el['full_name'] for el in authors if el.get('inspire_role') == 'editor']
    h_values = [el['full_name'] for el in authors if el.get('inspire_role') != 'editor']

    r_values = force_list(reference.get('report_numbers'))
    if reference.get('arxiv_eprint'):
        arxiv_eprint = reference['arxiv_eprint']
        r_values.append('arXiv:' + arxiv_eprint if is_arxiv_post_2007(arxiv_eprint) else arxiv_eprint)

    journal_title = get_value(reference, 'publication_info.journal_title')
    journal_volume = get_value(reference, 'publication_info.journal_volume')
    page_start = get_value(reference, 'publication_info.page_start')
    page_end = get_value(reference, 'publication_info.page_end')
    artid = get_value(reference, 'publication_info.artid')
    s_value = build_pubnote(journal_title, journal_volume, page_start, page_end, artid)

    m_value = ' / '.join(force_list(reference.get('misc')))

    return {
        '0': get_recid_from_ref(value.get('record')),
        'a': a_values,
        'b': get_value(reference, 'publication_info.cnum'),
        'c': reference.get('collaborations'),
        'e': e_values,
        'h': h_values,
        'i': reference.get('isbn'),
        'k': reference.get('texkey'),
        'm': m_value,
        'o': reference.get('label'),
        'p': get_value(reference, 'imprint.publisher'),
        'q': get_value(reference, 'publication_info.parent_title'),
        'r': r_values,
        's': s_value,
        't': get_value(reference, 'title.title'),
        'u': get_value(reference, 'urls.value'),
        'x': get_value(value, 'raw_refs.value'),
        'y': get_value(reference, 'publication_info.year'),
    }
