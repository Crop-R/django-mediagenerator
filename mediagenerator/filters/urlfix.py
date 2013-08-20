import re
import os
import posixpath
from hashlib import sha1

from django.conf import settings
from mimetypes import guess_type
from base64 import b64encode
from mediagenerator import settings as appsettings
from mediagenerator.generators.bundles.base import FileFilter
from mediagenerator.utils import media_url, prepare_patterns, find_file

JS_URL_PREFIX = getattr(settings, "MEDIA_JS_URL_FILTER_PREFIX", r"OTA\.")
GENERATE_DATA_URIS = getattr(settings, 'GENERATE_DATA_URIS', False)
MAX_DATA_URI_FILE_SIZE = getattr(settings, 'MAX_DATA_URI_FILE_SIZE', 12 * 1024)
IGNORE_PATTERN = prepare_patterns(getattr(settings,
   'IGNORE_DATA_URI_PATTERNS', (r'.*\.htc',)), 'IGNORE_DATA_URI_PATTERNS')


class UrlFixFilter(FileFilter):
    
    
    def get_dev_output(self, name, variation, content=None):
        
        if not content:
            content = super(UrlFixFilter, self).get_dev_output(name, variation)

        if name.startswith("admin-media"):
            return content



        rewriter = UrlRerwiter(name)
        return rewriter.rewrite(content)


class UrlRerwiter(object):
    
    re_css = re.compile(r'url\s*\((?P<d>["\'])?(?P<url>.*?)(?P=d)?\)', re.UNICODE)
    re_js  = re.compile(r'(MEDIA|OTA)\.(?P<type>url|import)\s*\((?P<d>["\'])(?P<url>.*?)(?P=d)\)', re.UNICODE)
    
    def __init__(self, name):
        self.name = name
        self.type = type
        self.roots = appsettings.GLOBAL_MEDIA_DIRS
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root and media_root not in self.roots:
            self.roots.append(media_root)

        self.base = os.path.dirname(name)

        if name.endswith(".css"):
            self.type = "css"
        elif name.endswith(".scss"):
            self.type = "css"
        elif name.endswith(".sass"):
            self.type = "css"
        elif name.endswith(".js"):
            self.type = "js"
        elif name.endswith(".jst"):
            self.type = "js"
        else:
            raise Exception("Unsupported filetype for UrlFixFilter: %s" % name)

    def rewrite(self, content): 
        if self.type == 'js':
            return self.re_js.sub(self._rewrite_js, content)
        else:
            return self.re_css.sub(self._rewrite_css, content)

    def _rewrite_css(self, match):
        url = match.group('url')
        if url.startswith("//") or url.startswith('data:image') or url.startswith("about:") or '$' in url:
            return "url(%s)" % url

        return "url(%s)" % self._rebase(url)

    def _rewrite_js(self, match):
        url = match.group('url')
        typ = match.group('type')

        if typ == 'url':
            if url.startswith('//'):
                return "'%s'" % url
            return "'%s'" % self._rebase(url)
        elif typ == 'import':
            return '\n'.join(['importScripts("%s");' % src for src in media_urls(url)])

    def _rebase(self, url):

        if "#" in url:
            url, hashid = url.rsplit("#", 1)
            hashid = "#" + hashid
        else:
            hashid = ""

        if "?" in url:
            url, _ = url.rsplit("?", 1)

	rebased = None
    if url.startswith("."):
        rebased = posixpath.join(self.base, url)
        rebased = posixpath.normpath(rebased)
    else:
        rebased = url.strip("/")

	path = None
	if '/' in self.name:  # try find file using relative url in self.name
	    path = find_file(os.path.join(self.name[:self.name.rindex('/')],rebased))
	    if path: rebased = os.path.join(self.name[:self.name.rindex('/')],rebased)

	if not path:  # try finding file based on GLOBAL_MEDIA_DIRS
	    path = find_file(rebased)
        
	if not path:
	    raise Exception("Unable to find url `%s` from file %s. File does not exists: %s" % (
	        url, 
	        self.name,
	        rebased
	    ))

	# generating data for images doesn't work for scss
    if getattr(settings, 'GENERATE_DATA_URIS', False) and self.name.endswith('.css'):
         if os.path.getsize(path) <= MAX_DATA_URI_FILE_SIZE and \
                not IGNORE_PATTERN.match(rebased):
            data = b64encode(open(path, 'rb').read())
            mime = guess_type(path)[0] or 'application/octet-stream'
            return 'data:%s;base64,%s' % (mime, data)
    elif getattr(settings, 'GENERATE_DATA_URIS', False) and self.name.endswith('.scss') and False:
        if os.path.getsize(path) <= MAX_DATA_URI_FILE_SIZE and not IGNORE_PATTERN.match(rebased):
	    return 'inline-image("%s")' % (url)



    if appsettings.MEDIA_DEV_MODE:
        prefix = appsettings.DEV_MEDIA_URL
        version = os.path.getmtime(path)
        rebased += "?v=%s" % version

    else:
        prefix = appsettings.PRODUCTION_MEDIA_URL
        with open(path) as sf:
            version = sha1(sf.read()).hexdigest()

        rebased_prefix, rebased_extention = rebased.rsplit(".", 1)
        rebased = "%s.%s" % (rebased_prefix, rebased_extention)

    rebased = posixpath.join(prefix, rebased)
    return "/" + rebased.strip("/") + hashid



