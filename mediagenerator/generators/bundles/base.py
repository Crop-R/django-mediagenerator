from .settings import DEFAULT_MEDIA_FILTERS
from django.utils.encoding import smart_str
from hashlib import sha1
from mediagenerator.settings import MEDIA_DEV_MODE
from mediagenerator.utils import load_backend, find_file, read_text_file
import os

class Filter(object):
    takes_input = True

    def __init__(self, **kwargs):
        self.file_filter = FileFilter
        self.config(kwargs, filetype=None, filter=None,
                            bundle=None, _from_default=None)

        # We assume that if this is e.g. a 'js' backend then all input must
        # also be 'js'. Subclasses must override this if they expect a special
        # input file type. Also, subclasses have to check if their file type
        # is supported.
        self.input_filetype = self.filetype

        if self.takes_input:
            self.config(kwargs, input=())
            if not isinstance(self.input, (tuple, list)):
                self.input = (self.input,)
        self._input_filters = None
        assert not kwargs, 'Unknown parameters: %s' % ', '.join(kwargs.keys())

    @classmethod
    def from_default(cls, name):
        return {'input': name}

    def should_use_default_filter(self, ext):
        return ext != self._from_default

    def get_variations(self):
        """
        Returns all possible variations that get generated by this filter.

        The result must be a dict whose values are tuples.
        """
        return {}

    def get_output(self, variation):
        """
        Yields content for each output item for the given variation.
        """
        raise NotImplementedError()

    def get_dev_output(self, name, variation):
        """
        Returns content for the given file name and variation in development mode.
        """
        index, child = name.split('/', 1)
        index = int(index)
        filter = self.get_input_filters()[index]
        return filter.get_dev_output(child, variation)

    def get_dev_output_names(self, variation):
        """
        Yields file names for the given variation in development mode.
        """
        # By default we simply return our input filters' file names
        for index, filter in enumerate(self.get_input_filters()):
            for name, hash in filter.get_dev_output_names(variation):
                yield '%d/%s' % (index, name), hash

    def get_input(self, variation):
        """Yields contents for each input item."""
        for filter in self.get_input_filters():
            for input in filter.get_output(variation):
                yield input

    def get_input_filters(self):
        """Returns a Filter instance for each input item."""
        if not self.takes_input:
            raise ValueError("The %s media filter doesn't take any input" %
                             self.__class__.__name__)
        if self._input_filters is not None:
            return self._input_filters
        self._input_filters = []
        for input in self.input:
            if isinstance(input, dict):
                filter = self.get_filter(input)
            else:
                filter = self.get_item(input)
            self._input_filters.append(filter)
        return self._input_filters

    def get_filter(self, config):
        backend_class = load_backend(config.get('filter'))
        return backend_class(filetype=self.input_filetype, bundle=self.bundle,
                             **config)

    def get_item(self, name):
        ext = os.path.splitext(name)[1].lstrip('.')
        backend_classes = []

        if ext in DEFAULT_MEDIA_FILTERS and self.should_use_default_filter(ext):
            ext_class = DEFAULT_MEDIA_FILTERS[ext]
            if isinstance(ext_class, basestring):
                backend_classes.append(load_backend(DEFAULT_MEDIA_FILTERS[ext]))
            elif isinstance(ext_class, tuple):
                backend_classes.append(FilterPipe)
                for pipe_entry in ext_class:
                    backend_classes.append(load_backend(pipe_entry))
        else:
            backend_classes.append(self.file_filter)


        backends = []
        for backend_class in backend_classes:
            config = backend_class.from_default(name)
            config.setdefault('filter',
                '%s.%s' % (backend_class.__module__, backend_class.__name__))
            config.setdefault('filetype', self.input_filetype)
            config['bundle'] = self.bundle
            # This is added to make really sure we don't instantiate the same
            # filter in an endless loop. Normally, the child class should
            # take care of this in should_use_default_filter().
            config.setdefault('_from_default', ext)
            backends.append(backend_class(**config))

        backend = backends.pop(0)
        for pipe_entry in backends:
            backend.grow_pipe(pipe_entry)

        return backend


    def _get_variations_with_input(self):
        """Utility function to get variations including input variations"""
        variations = self.get_variations()
        if not self.takes_input:
            return variations

        for filter in self.get_input_filters():
            subvariations = filter._get_variations_with_input()
            for k, v in subvariations.items():
                if k in variations and v != variations[k]:
                    raise ValueError('Conflicting variations for "%s": %r != %r' % (
                        k, v, variations[k]))
            variations.update(subvariations)
        return variations

    def config(self, init, **defaults):
        for key in defaults:
            setattr(self, key, init.pop(key, defaults[key]))

class FileFilter(Filter):
    """A filter that just returns the given file."""
    takes_input = False

    def __init__(self, **kwargs):
        self.config(kwargs, name=None)
        self.mtime = self.hash = None
        super(FileFilter, self).__init__(**kwargs)

    @classmethod
    def from_default(cls, name):
        return {'name': name}

    def get_output(self, variation):
        yield self.get_dev_output(self.name, variation)

    def get_dev_output(self, name, variation):
        assert name == self.name, (
            '''File name "%s" doesn't match the one in GENERATE_MEDIA ("%s")'''
            % (name, self.name))
        return read_text_file(self._get_path())

    def get_last_modified(self):
        path = self._get_path()
        return os.path.getmtime(path)

    def get_dev_output_names(self, variation):
        mtime = self.get_last_modified()
        # In dev mode, where a lot of requests
        # we can reduce proc time of filters
        # making hash = mtime of source file 
        # instead of sha1(filtered_content)
        if MEDIA_DEV_MODE:
            hash = str(mtime)
        elif mtime != self.mtime:
            output = self.get_dev_output(self.name, variation)
            hash = sha1(smart_str(output)).hexdigest()
        else:
            hash = self.hash
        yield self.name, hash

    def _get_path(self):
        path = find_file(self.name)
        assert path, """File name "%s" doesn't exist.""" % self.name
        return path

class RawFileFilter(FileFilter):
    takes_input = False

    def __init__(self, **kwargs):
        self.config(kwargs, path=None)
        super(RawFileFilter, self).__init__(**kwargs)

    def get_dev_output(self, name, variation):
        assert name == self.name, (
            '''File name "%s" doesn't match the one in GENERATE_MEDIA ("%s")'''
            % (name, self.name))
        return read_text_file(self.path)

    def get_dev_output_names(self, variation):
        mtime = os.path.getmtime(self.path)
        if mtime != self.mtime:
            output = self.get_dev_output(self.name, variation)
            hash = sha1(smart_str(output)).hexdigest()
        else:
            hash = self.hash
        yield self.name, hash

class FilterPipe(FileFilter):
    
    def __init__(self, **kwargs):
        super(FilterPipe, self).__init__(**kwargs)
        self.pipe = []

    def grow_pipe(self, pipe_entry):
        self.pipe.append(pipe_entry)

    def get_dev_output(self, name, variation):
        output = super(FilterPipe, self).get_dev_output(name, variation)
        for filter in self.pipe:
            output = filter.get_dev_output(name, variation, content=output)

        return output

    def get_last_modified(self):
        lmod = 0
        for entry in self.pipe:
            entry_lm = entry.get_last_modified()
            if entry_lm > lmod:
                lmod = entry_lm
        
        return lmod
