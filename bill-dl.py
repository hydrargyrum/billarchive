#!/usr/bin/env python3

import datetime
from logging import getLogger
from pathlib import Path
import mimetypes

import magic
from weboob.capabilities.bill import CapDocument
from weboob.tools.application.repl import ReplApplication


def to_datetime(obj):
    if isinstance(obj, datetime.date):
        obj = datetime.datetime.combine(obj, datetime.time())
    return obj


def check_mime(filename, sample):
    actual = magic.detect_from_content(sample)
    guess = mimetypes.guess_type(filename)
    return guess[0] == actual.mime_type


class BackendDownloader:
    def __init__(self, backend, config):
        self.backend = backend
        self.config = config
        self.logger = getLogger(f'downloader.{backend.name}')

    def get_date_until(self, subscription):
        return datetime.datetime.min

    def get_backend_config(self, option, default):
        return self.config.get(self.backend.name, option, default=default)

    def root_path(self):
        path = self.get_backend_config('dir', None)
        if path:
            return Path(path)

        path = self.config.get('dir', default=None)
        if path:
            path = Path(path)
        else:
            path = Path.cwd()
        return path / self.backend.name

    def download_document(self, subscription, document):
        path = (self.root_path() / subscription.id / f"{document.id}.{document.format}")
        if not document.has_file:
            self.logger.info('%s document has no file, no download', document)
            return

        if path.exists():
            self.logger.info('%s already exists for document %s, no download', path, document)
            return

        self.logger.info('downloading %s to %s', document, path)
        # TODO option to force pdf?
        data = self.backend.download_document(document)
        if not data:
            self.logger.info('none data for %s', document)
            return

        if not check_mime(path.name, data):
            # typically happens if reaching an html error page (with 200 status)
            # while expecting a pdf document
            self.logger.warning('unexpected MIME type for %r, considering corrupt download', document)
            return

        path.write_bytes(data)
        self.logger.info('successfully downloaded %s', document)

    def download_subscription(self, subscription):
        self.logger.debug('downloading subscription %s', subscription)
        (self.root_path() / subscription.id).mkdir(exist_ok=True)

        for document in self.backend.iter_documents(subscription):
            # TODO timezones?
            if document.date and to_datetime(document.date) < self.get_date_until(subscription):
                self.logger.info('reached date threshold for %r', subscription)
                break

            self.download_document(subscription, document)

    def download(self):
        self.logger.debug('downloading backend %s', self.backend)
        self.root_path().mkdir(exist_ok=True)
        for subscription in self.backend.iter_subscription():
            self.download_subscription(subscription)


class BillDlApp(ReplApplication):
    APPNAME = 'bill-dl'
    VERSION = '0.1'
    COPYRIGHT = 'Copyleft weboob project'
    CAPS = (CapDocument,)

    def do_download(self, _):
        """Download documents"""

        def download(backend):
            return BackendDownloader(backend, self.config).download()

        for _ in self.do(download):
            pass

    def main(self, argv):
        self.load_config()
        return super().main(argv)


BillDlApp.run()
