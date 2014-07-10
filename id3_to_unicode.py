#!/usr/bin/env python
#
#     id3_to_unicode.py -- change encoding of mp3 iD tags to unicode
#
# $Id: id3_to_unicode.py 259 2011-08-20 08:54:25Z lenik $

import os, sys, argparse, shutil

try :
    import codecs, chardet
    import eyed3.mp3, eyed3.id3  # mp3 iD tag processing
except ImportError, e :
    print 'please, install python-%s' % str(e).split()[-1].lower()
    sys.exit()

def main():
    path = os.path.abspath(os.path.curdir)
    parser = argparse.ArgumentParser(description='change encoding of mp3 iD3 tags to unicode')
    parser.add_argument('-r', '--recursive', help='search recursively', action='store_true')
    parser.add_argument('-u', '--update', help='update mp3 files', action='store_true')
    parser.add_argument('-o', '--overwrite', help='overwrite tags from Artist/Album/Title directory structure', action='store_true')
    parser.add_argument('-R', '--rename', help='rename file as well', action='store_true')
    parser.add_argument('-f', '--force', help='treat files as mp3', action='store_true')
    parser.add_argument('-e', '--encoding', help='always assume this encoding')    
    parser.add_argument('location', type=str, nargs='?', default=path, help='search directory (default:%(default)s)')

    args = parser.parse_args()
    
    if args.encoding:
        try:
            codecs.lookup(args.encoding)
        except:
            print "Don't know how to deal with '%s' codec"%(args.encoding)
            return
    
    init()
    
    process(args)

def init():
    import warnings  # UnicodeWarning: Unicode unequal comparison failed, blah-blah...
    warnings.filterwarnings('ignore', category=UnicodeWarning)

    sys.stdout = codecs.getwriter("UTF8")(sys.stdout)

def process(args):
    try:
        for root, dirs, files in os.walk(args.location) :
            dirs
            if not len(files) : continue
            print "entering '%s'"%(unicode(root, 'utf-8'))
            stats = dict()
            fset = []
            for name in files:
                if name.lower().endswith('mp3'):
                    aname = alternative(name)
                    fn = os.path.join(root, name)
                    collect_stats(args, stats, fn, aname)
                    if aname and aname != name and args.rename:
                        nfn = os.path.join(root, aname)
                        shutil.move(fn, nfn)
                        fn = nfn
                    fset.append(fn)
    
            if len(stats) :
                stats = [(stats[i], i) for i in stats]
                stats = sorted(stats, reverse=True)
                total = sum([i[0] for i in stats]) + 0.0001
                stats = [(i[0] * 100 / total, i[1]) for i in stats]

                if args.encoding:
                    encoding = args.encoding
                else:
                    encoding = select_encoding(root, stats)
                for fname in fset:
                    convert(args, fname, encoding)
            else :
                print unicode(root, 'utf-8'), ': nothing to convert or already in unicode/ascii',
            print
            if not args.recursive :
                break
    
    except KeyboardInterrupt :
        print 'Ctrl/C was pressed, aborting...'
        pass


def alternative(txt):
    det = chardet.detect(txt)
    try :
        bs = ''.join([chr(ord(i)) for i in txt.decode(det['encoding'])])
    except ValueError :
        return None
    ddet = chardet.detect(bs)
    if ddet['encoding'] == 'ascii': return None
    return bs.decode(ddet['encoding'])

def unicode2bytestring(string) :
    if string is None: string = ''
    try :
        string = ''.join([chr(ord(i)) for i in string])
    except ValueError :
        pass  # unicode fails chr(ord()) conversion
    return string

def make_unicode(string, encoding) :
    try :
        string = unicode(string, encoding)
    except :
        pass  # bad encoding, do nothing
    return string

def convert(args, file_name, encoding) :
    print unicode(file_name, "utf-8"),
    if not eyed3.mp3.isMp3File(file_name) and not args.force:
        print ': not an MP3 file'
        return

    afile = eyed3.load(file_name)
    tag = afile.tag
    if tag is None:
        print ': has not tag'
        return
    tag.header.version = eyed3.id3.ID3_V2_3

    artist = unicode2bytestring(tag.artist)
    album = unicode2bytestring(tag.album)
    title = unicode2bytestring(tag.title)
    try:
        original = ''.join((artist, album, title))
    except:
        original = None

#     artist = artist.replace( '-', '' )
#     album = album.replace( '[+digital booklet]', '2010' )

    artist = make_unicode(artist, encoding)
    album = make_unicode(album, encoding)
    title = make_unicode(title, encoding)

    head, tail = os.path.split(os.path.abspath(file_name))
    if args.overwrite or not len(title) :
        title = unicode(tail, 'utf-8')[:-4]  # strip trailing ".mp3"
        if title[0] in '0123456789' and title[1] in '0123456789' and title[2] == ' ' :
            title = title[3:]  # strip leading track number

    head, tail = os.path.split(head)
    if args.overwrite or not len(album) :
        album = unicode(tail, 'utf-8')

    head, tail = os.path.split(head)
    if args.overwrite or not len(artist) :
        artist = unicode(tail, 'utf-8')

    if original != ''.join((artist, album, title)) :
        if args.update :
            # eyed3.tag.TagException: ID3 v1.x supports ISO-8859 encoding only
            tag.version = eyed3.id3.ID3_V2_4
            tag.artist = artist
            tag.album = album
            tag.title = title
            tag.save(encoding='utf8')
        print '->',
    else :
        print '==',

    print artist, ':', album, ':', title

def collect_stats(args, stats, file_name, altname) :
    if not eyed3.mp3.isMp3File(file_name) and not args.force:
        print unicode(altname or file_name, "utf-8"), ': not an MP3 file'
        return

    try:
        afile = eyed3.load(file_name)
        tag = afile.tag
        if tag is None:
            print "no tag in this file: '%s'" % (altname or os.path.basename(file_name))
            return
    except Exception, e :
        print unicode(altname or file_name, "utf-8"), ':', str(e)
        return

    for i in (tag.artist, tag.album, tag.title) :
        try:
            enc = chardet.detect(unicode2bytestring(i))
        except Exception, e:
            print unicode(altname or file_name, "utf-8"), ':', str(e)
            return

        if enc['encoding'] == 'ascii' and not args.overwrite : continue

        if enc['encoding'] == None : enc['encoding'] = 'None'

        if enc['encoding'] in stats :
            stats[enc['encoding']] += enc['confidence']
        else :
            stats[enc['encoding']] = enc['confidence']

def select_encoding(root, stats) :
    if len(stats) == 1 :  # only one encoding is available
        return stats[0][1]

    if stats[0][0] - stats[1][0] > 40 :  # more than 40% difference
        return stats[0][1]

    stats = [i for i in stats if i[1] != 'None']

    print unicode(root, 'utf-8'), ": several encodings are possible:"
    for i in xrange(len(stats)) :
        print "%d. %s (%5.2f%%)" % (i + 1, stats[i][1], stats[i][0])

    while True :
        print 'select encoding (1..%d):' % (len(stats)),
        encoding = int(raw_input()) - 1
        try :
            print stats[encoding][1], 'selected'
            break
        except:
            pass
    return stats[encoding][1]

if __name__ == '__main__':
    main()
