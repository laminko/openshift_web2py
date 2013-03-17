"""
This file is part of the web2py Web Framework
Copyrighted by Massimo Di Pierro <mdipierro@cs.depaul.edu>
License: LGPLv3 (http://www.gnu.org/licenses/lgpl.html)
"""
import datetime
import decimal
from storage import Storage
from html import TAG, XmlComponent
from html import xmlescape
from languages import lazyT
import contrib.rss2 as rss2

try:
    import json as json_parser                      # try stdlib (Python 2.6)
except ImportError:
    try:
        import simplejson as json_parser            # try external module
    except:
        import contrib.simplejson as json_parser    # fallback to pure-Python module

have_yaml = True
try:
    import yaml as yamlib
except ImportError:
    have_yaml = False

def cast_keys(o, cast=str, encoding="utf-8"):
    """ Builds a new object with <cast> type keys

    Arguments:
        o is the object input
        cast (defaults to str) is an object type or function
              which supports conversion such as:

              >>> converted = cast(o)

        encoding (defaults to utf-8) is the encoding for unicode
                 keys. This is not used for custom cast functions

    Use this funcion if you are in Python < 2.6.5
    This avoids syntax errors when unpacking dictionary arguments.
    """

    if isinstance(o, (dict, Storage)):
        if isinstance(o, dict):
            newobj = dict()
        else:
            newobj = Storage()

        for k, v in o.items():
            if (cast == str) and isinstance(k, unicode):
                key = k.encode(encoding)
            else:
                key = cast(k)
            if isinstance(v, (dict, Storage)):
                value = cast_keys(v, cast=cast, encoding=encoding)
            else:
                value = v
            newobj[key] = value
    else:
        raise TypeError("Cannot cast keys: %s is not supported" % \
                        type(o))
    return newobj

def loads_json(o, unicode_keys=True, **kwargs):
    # deserialize a json string
    result = json_parser.loads(o, **kwargs)
    if not unicode_keys:
        # filter non-str keys in dictionary objects
        result = cast_keys(result,
                           encoding=kwargs.get("encoding", "utf-8"))
    return result

def custom_json(o):
    if hasattr(o, 'custom_json') and callable(o.custom_json):
        return o.custom_json()
    if isinstance(o, (datetime.date,
                      datetime.datetime,
                      datetime.time)):
        return o.isoformat()[:19].replace('T', ' ')
    elif isinstance(o, (int, long)):
        return int(o)
    elif isinstance(o, decimal.Decimal):
        return str(o)
    elif isinstance(o, lazyT):
        return str(o)
    elif isinstance(o, XmlComponent):
        return str(o)
    elif hasattr(o, 'as_list') and callable(o.as_list):
        return o.as_list()
    elif hasattr(o, 'as_dict') and callable(o.as_dict):
        return o.as_dict()
    else:
        raise TypeError(repr(o) + " is not JSON serializable")


def xml_rec(value, key, quote=True):
    if hasattr(value, 'custom_xml') and callable(value.custom_xml):
        return value.custom_xml()
    elif isinstance(value, (dict, Storage)):
        return TAG[key](*[TAG[k](xml_rec(v, '', quote))
                          for k, v in value.items()])
    elif isinstance(value, list):
        return TAG[key](*[TAG.item(xml_rec(item, '', quote)) for item in value])
    elif hasattr(value, 'as_list') and callable(value.as_list):
        return str(xml_rec(value.as_list(), '', quote))
    elif hasattr(value, 'as_dict') and callable(value.as_dict):
        return str(xml_rec(value.as_dict(), '', quote))
    else:
        return xmlescape(value, quote)


def xml(value, encoding='UTF-8', key='document', quote=True):
    return ('<?xml version="1.0" encoding="%s"?>' % encoding) + str(xml_rec(value, key, quote))


def json(value, default=custom_json):
    # replace JavaScript incompatible spacing
    # http://timelessrepo.com/json-isnt-a-javascript-subset
    return json_parser.dumps(value,
        default=default).replace(ur'\u2028',
                                 '\\u2028').replace(ur'\2029',
                                                    '\\u2029')

def csv(value):
    return ''


def ics(events, title=None, link=None, timeshift=0, **ignored):
    import datetime
    title = title or '(unkown)'
    if link and not callable(link):
        link = lambda item, prefix=link: prefix.replace(
            '[id]', str(item['id']))
    s = 'BEGIN:VCALENDAR'
    s += '\nVERSION:2.0'
    s += '\nX-WR-CALNAME:%s' % title
    s += '\nSUMMARY:%s' % title
    s += '\nPRODID:Generated by web2py'
    s += '\nCALSCALE:GREGORIAN'
    s += '\nMETHOD:PUBLISH'
    for item in events:
        s += '\nBEGIN:VEVENT'
        s += '\nUID:%s' % item['id']
        if link:
            s += '\nURL:%s' % link(item)
        shift = datetime.timedelta(seconds=3600 * timeshift)
        start = item['start_datetime'] + shift
        stop = item['stop_datetime'] + shift
        s += '\nDTSTART:%s' % start.strftime('%Y%m%dT%H%M%S')
        s += '\nDTEND:%s' % stop.strftime('%Y%m%dT%H%M%S')
        s += '\nSUMMARY:%s' % item['title']
        s += '\nEND:VEVENT'
    s += '\nEND:VCALENDAR'
    return s


def rss(feed):
    if not 'entries' in feed and 'items' in feed:
        feed['entries'] = feed['items']
    now = datetime.datetime.now()
    rss = rss2.RSS2(title=str(feed.get('title', '(notitle)')),
                    link=str(feed.get('link', None)),
                    description=str(feed.get('description', '')),
                    lastBuildDate=feed.get('created_on', now),
                    items=[rss2.RSSItem(
                           title=str(entry.get('title', '(notitle)')),
                           link=str(entry.get('link', None)),
                           description=str(entry.get('description', '')),
                           pubDate=entry.get('created_on', now)
                           ) for entry in feed.get('entries', [])])
    return rss.to_xml(encoding='utf-8')

def yaml(data):
    if have_yaml:
        return yamlib.dump(data)
    else: raise ImportError("No YAML serializer available")

def loads_yaml(data):
    if have_yaml:
        return yamlib.load(data)
    else: raise ImportError("No YAML serializer available")

