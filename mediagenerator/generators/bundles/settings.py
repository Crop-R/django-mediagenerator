from django.conf import settings

DEFAULT_MEDIA_FILTERS = getattr(settings, 'DEFAULT_MEDIA_FILTERS', {
    'ccss': 'mediagenerator.filters.clever.CleverCSS',
    'coffee': 'mediagenerator.filters.coffeescript.CoffeeScript',
    'css': 'mediagenerator.filters.cssurl.CSSFilePipe',
    'html': 'mediagenerator.filters.template.Template',
    'py': 'mediagenerator.filters.pyjs_filter.Pyjs',
    'pyva': 'mediagenerator.filters.pyvascript_filter.PyvaScript',
    'sass': 'mediagenerator.filters.sass.Sass',
    'scss': 'mediagenerator.filters.sass.Sass',
    'less': 'mediagenerator.filters.less.Less',
    'sprite': 'mediagenerator.filters.sprite.Sprite',
})

DEFAULT_CSS_PIPE = getattr(settings, 'DEFAULT_CSS_PIPE', (
    'mediagenerator.filters.cssurl.CSSURLFileFilter',
    'mediagenerator.filters.sprite.CSSSprite',
))

ROOT_MEDIA_FILTERS = getattr(settings, 'ROOT_MEDIA_FILTERS', {})

# These are applied in addition to ROOT_MEDIA_FILTERS.
# The separation is done because we don't want users to
# always specify the default filters when they merely want
# to configure YUICompressor or Closure.
BASE_ROOT_MEDIA_FILTERS = getattr(settings, 'BASE_ROOT_MEDIA_FILTERS', {
    '*': 'mediagenerator.filters.concat.Concat',
    'css': 'mediagenerator.filters.cssurl.CSSURL',
})

MEDIA_BUNDLES = getattr(settings, 'MEDIA_BUNDLES', ())