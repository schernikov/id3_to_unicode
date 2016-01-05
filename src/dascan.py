'''
Created on Mar 20, 2015

@author: schernikov
'''

import sys, eyed3.utils, chardet, transliterate, os, argparse
import cPickle
#import langdetect

minconfidence = 0.8

def main():
    parser = argparse.ArgumentParser(description='change encoding of mp3 iD3 tags to unicode')
    parser.add_argument('location', type=str, help='search directory')    
    args = parser.parse_args()

    loc = args.location

    fname = os.path.join(loc, 'tags.picle')
    if os.path.isfile(fname):
        sep = "="*80
        print sep
        print "reading from %s"%(fname)
        print sep
        with open(fname) as f:
            tagset = cPickle.load(f)

    else:
        handler = Handler(loc)
        
        eyed3.utils.walk(handler, loc, fs_encoding=sys.getfilesystemencoding())
        tagset = handler.tagset
        with open(fname ,'wb') as f:
            cPickle.dump(tagset, f)
            
        print handler.count
            
    tagnames = {}
    with open(os.path.join(os.path.dirname(__file__), 'tags.txt')) as f:
        for line in f.readlines():
            ln = line.strip()
            idx = ln.find(',')
            if idx < 0: continue
            tag = ln[:idx].strip()
            desc = ln[idx+1:].strip()
            if not tag or not desc: continue
            tagnames[tag] = desc
            
    for nm, group in tagset.items():
        desc = tagnames.get(nm, '')
        print '%s %d "%s"'%(nm, len(group), desc)
        for el in list(group)[:100]:
            process(el)
        print


def process(txt):
    if not txt: return

    if type(txt) == unicode:
        u = txt
        detect(u, 'U')
    else:
        det = chardet.detect(txt)
        if det['encoding'] == 'utf-8':
            if det['confidence'] > minconfidence:
                # it is utf-8 but is it valid?
                u = unicode(txt, 'utf-8')
                detect(u, 'utf-8')
            else:
                raise Exception('this is really unexpected')
        else:
            decoded(txt, txt, det)


def detect(u, enc):
    asc = encdet(u, ['ascii'])
    if asc is not None:
        if translit(u): return
    else:
        raw = ununicode(u)
        if raw:
            det = chardet.detect(raw)
            if det['confidence'] > minconfidence:
                decoded(u, raw, det)
                return
    plain(u, enc)

            
def plain(u, enc):
    print '  %s --> (%s)'%(u, enc)
            

def decoded(orig, txt, det):
    enc = det['encoding']
    new = unicode(txt, enc)
    print '  %s --> [%s] %s'%(orig, enc, new)


def translit(u):
    t = transliterate.translit(u, 'ru')

    ru = encdet(t, ['windows-1251'])

    if ru is not None:
        # seems valid after transliteration
        print '  %s --> %s'%(u, t)
        return True
    return False

    #blang = max(langdetect.detect_langs(u), key=lambda l: l.prob)    
    #alang = max(langdetect.detect_langs(t), key=lambda l: l.prob)
    #if alang.prob > blang.prob:
    #    return t

    
def encdet(txt, encs):
    maxed = None
    for enc in encs:
        try:
            new = txt.encode(enc)
            det = chardet.detect(new)
            if det['confidence'] > minconfidence and enc == det['encoding']:
                if maxed is None:
                    maxed = (det['confidence'], enc)
                else:
                    if maxed[0] < det['confidence']:
                        maxed = (det['confidence'], enc)
        except UnicodeEncodeError:
            pass

    return maxed
        


def ununicode(u):
    try:
        return ''.join([chr(ord(i)) for i in u])
    except:
        return None


class Coder(object):
    
    def __init__(self, name, coder):
        self.name = name
        self.coder = coder


class Handler(eyed3.utils.FileHandler):

    def __init__(self, root):
        self._root = root
        self.count = 0
        self.tagset = {}
    
    def handleFile(self, fname):
        afile = eyed3.load(fname)
        if not afile: return
        #print "[%d] %s"%(self.count, os.path.relpath(fname, self._root))
        tag = afile.tag
        if not tag: return
        
        self._push('TPE1', tag.artist)
        self._push('TALB', tag.album)
        self._push('TIT2', tag.title)

        for fnm, frs in tag.frame_set.items():
            for fr in frs:
                if not hasattr(fr, 'text'): continue
                self._push(fnm, fr.text)
        
        self.count += 1
        
    def _push(self, tg, text):
        tgo = self.tagset.get(tg, None)
        if tgo is None:
            tgo = set()
            self.tagset[tg] = tgo
        if text: 
            txt = text.strip()
            if txt: tgo.add(txt)


def onaccessor(acc):
    for cm in acc:
        cm.text


if __name__ == '__main__':
    main()
