from django.conf import settings
from django.utils.encoding import smart_str
from mediagenerator.generators.bundles.base import Filter
from os import path, makedirs
import hashlib
from . import yuicompressor
import codecs

DIR = '/tmp/mediagenerator/'
if not path.isdir(DIR):
    makedirs(DIR)

class CacheMixin(object):
    def __init__(self, **kwargs):
        super(CacheMixin, self).__init__(**kwargs)
        self.__fake_inputs = None

    def get_cached(self, key):
        p = DIR + key
        return codecs.open(p, 'r', encoding='utf-8').read() if path.isfile(p) else None

    def write_cache(self, key, value):
        p = DIR + key
        with codecs.open(p, 'w', encoding='utf-8') as f:
            f.write(value)

    def get_output(self, variation):
        inputs = [smart_str(i) for i in super(CacheMixin, self).get_input(variation)]
        keys = [hashlib.sha1(string).hexdigest() for string in inputs]
        outputs = [self.get_cached(key) for key in keys]
        assert self.__fake_inputs is None, "__fake_inputs set, unexpected recursion?"
        self.__fake_inputs = [inputs[i] for i,v in enumerate(outputs) if v is None]

        new_outputs = list(super(CacheMixin, self).get_output(variation))
        assert len(new_outputs) + len([o for o in outputs if o is not None]) == len(inputs)
        for i, output in enumerate(outputs):
            if output == None:
                output = new_outputs.pop(0)
                self.write_cache(keys[i], output)
            yield output
        self.__fake_inputs = None

    def get_input(self, variation):
        if self.__fake_inputs is not None:
            return self.__fake_inputs
        return super(CacheMixin, self).get_inputs(variation)

class YUICompressor(CacheMixin, yuicompressor.YUICompressor):
    pass
