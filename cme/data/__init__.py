"""This package contains types and functions to load data in different
formats and converts them to our internal representation which than can be
used for message extraction"""

from cme.data.json import read_transcripts_json, read_transcripts_json_file
from cme.data.xml import read_transcript_xml_file


