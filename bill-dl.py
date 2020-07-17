#!/usr/bin/env python3

from pathlib import Path

from weboob.capabilities.bill import CapDocument
from weboob.tools.application.repl import ReplApplication


class BillDlApp(ReplApplication):
    APPNAME = 'bill-dl'
    VERSION = '0.1'
    COPYRIGHT = 'Copyleft weboob project'
    CAPS = (CapDocument,)

    def root_path(self):
        return Path.cwd()

    def download_document(self, backend, subscription, document):
        path = (self.root_path() / backend.name / subscription.id / f"{document.id}.{document.format}")
        if not document.has_file:
            self.logger.info('%s document has no file, no download', document)
            return

        if path.exists():
            self.logger.info('%s already exists for document %s, no download', path, document)
            return

        self.logger.info('downloading %s to %s', document, path)
        data = backend.download_document(document)
        if not data:
            self.logger.info('none data for %s', document)
            return

        path.write_bytes(data)
        self.logger.info('successfully downloaded %s', document)

    def download_subscription(self, backend, subscription):
        self.logger.debug('downloading subscription %s', subscription)
        (self.root_path() / backend.name / subscription.id).mkdir(exist_ok=True)
        for document in backend.iter_documents(subscription):
            self.download_document(backend, subscription, document)

    def download_backend(self, backend):
        self.logger.debug('downloading backend %s', backend)
        (self.root_path() / backend.name).mkdir(exist_ok=True)
        for subscription in backend.iter_subscription():
            self.download_subscription(backend, subscription)

    def do_download(self, _):
        """Download documents"""
        for _ in self.do(self.download_backend):
            pass


BillDlApp.run()
