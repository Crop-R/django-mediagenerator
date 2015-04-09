from django.conf import settings
from django.utils.encoding import smart_str
from mediagenerator.generators.bundles.base import Filter
import socket
import time
from .yuicompressor import YUICompressor
import subprocess
import os

class YUICompressorClient(YUICompressor):
    def __init__(self, **kwargs):
        super(YUICompressorClient, self).__init__(**kwargs)
        self.yui_compressor_server = ('localhost', 7999)
        if getattr(settings, 'YUI_COMPRESSOR_SERVER', None):
            self.yui_compressor_server = (settings.YUI_COMPRESSOR_SERVER, 7999)

    @classmethod
    def start_server(cls):
        devnull = None
        if getattr(settings, 'YUI_COMPRESSOR_SERVER_PATH', None):
            if not devnull:
                devnull = open(os.devnull, 'w')
            subprocess.Popen(["java", "-jar", settings.YUI_COMPRESSOR_SERVER_PATH, '7999'], close_fds=True, stdin=devnull, stdout=devnull, stderr=devnull, preexec_fn=os.setpgrp)
            # os.system("java -jar %s 7999 &" % settings.YUI_COMPRESSOR_SERVER_PATH)
            time.sleep(2)
        else:
            raise ValueError("Failed to configure YUI_COMPRESSOR_SERVER_PATH")

    def get_connection(self):
        for i in xrange(1, 3):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(self.yui_compressor_server)
                return s
            except socket.error, e:
                if i == 1:
                    s = YUICompressorClient.start_server()
                    time.sleep(1)
        raise ValueError("Could not connect to server")

    def get_output(self, variation):
        for input in self.get_input(variation):
            try:
                s = self.get_connection();
                s.sendall('\n'.join(['file.%s\n' % self.filetype,
                                     smart_str(input),
                                     '\n\0\n']))
                chunks = []
                while True:
                    chunk = s.recv(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                output = ''.join(chunks)
                s.close()
                yield output.decode('utf-8')
            except Exception, e:
                import traceback
                traceback.print_exc()
                raise ValueError("Could not communicate with YUI_COMPRESSOR_SERVER\n"
                    "Error was: %s" % e)
        
