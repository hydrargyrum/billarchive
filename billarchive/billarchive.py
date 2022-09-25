#!/usr/bin/env python3

# This program is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://www.wtfpl.net/ for more details.

import datetime
from decimal import Decimal
from logging import getLogger
from pathlib import Path
import mimetypes
import re
from string import Formatter

from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
import magic
from woob.capabilities.base import empty, BaseObject
from woob.capabilities.bill import CapDocument
from woob.tools.application.repl import ReplApplication

from . import __version__


def to_datetime(obj):
    if isinstance(obj, datetime.date):
        obj = datetime.datetime.combine(obj, datetime.time())
    return obj


def check_mime(filename, sample):
    actual = magic.detect_from_content(sample)
    guess = mimetypes.guess_type(filename)
    return guess[0] == actual.mime_type


def to_dict(obj):
    def convert(obj):
        if empty(obj):
            return None
        elif isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, BaseObject):
            # TODO circular references
            return to_dict(obj)
        return obj

    return {
        k: convert(v)
        for k, v in obj.iter_fields()
        if not empty(v)
    }


duration_re = re.compile(r'(?P<quantity>\d+) (?P<unit>days?|months?|years?)')


def parse_date_since(s):
    match = duration_re.fullmatch(s)
    if match:
        unit = match['unit']
        if not unit.endswith('s'):
            unit += 's'
        return datetime.date.today() - relativedelta(**{unit: int(match['quantity'])})

    try:
        return parse_date(s)
    except ValueError:
        pass


class FilenameFormatter(Formatter):
    def convert_field(self, value, conv):
        protect = conv is None and isinstance(value, str)

        if conv == "u":
            conv = None

        if protect:
            value = value.replace("/", "_slash_")
            if value.startswith("."):
                value = f"dot_{value[1:]}"
            return value
        else:
            return super().convert_field(value, conv)


class BackendDownloader:
    default_filename = '{subscription.id}/{document.id}.{extension}'

    def __init__(self, backend, app):
        self.backend = backend
        self.config = app.config
        self.storage = app.storage
        self.logger = getLogger(f'downloader.{backend.name}')
        self.app = app

    def get_date_until(self, subscription, is_initial=False):
        option = 'sync_until'
        if is_initial:
            option = 'initial_sync_until'

        v = None
        s = self.get_backend_config(option, default=None)
        if s:
            v = parse_date_since(s)

        if not v:
            v = datetime.datetime.min
        return v

    def get_backend_config(self, option, default):
        missing = object()
        ret = self.config.get(self.backend.name, option, default=missing)
        if ret is missing:
            ret = self.config.get(option, default=default)
        return ret

    def root_path(self):
        path = self.config.get(self.backend.name, 'dir', default=None)
        if path:
            return Path(path).expanduser()

        path = self.config.get('dir', default=None)
        if path:
            path = Path(path).expanduser()
        else:
            path = Path.cwd()
        return path / self.backend.name

    def _set_meta_info(self, prefix):
        now = datetime.datetime.now()
        self.storage.set(*prefix, 'info', 'last_seen', now)
        if not self.storage.get(*prefix, 'info', 'first_seen', default=None):
            self.storage.set(*prefix, 'info', 'first_seen', now)

    def is_accepted_type(self, document):
        accepted_types = self.get_backend_config('accepted_types', default='').strip().lower()
        if not accepted_types:
            return True

        return (document.type or '').lower() in accepted_types.split()

    def download_document(self, subscription, document):
        formatter = FilenameFormatter()

        store_prefix = ('db', self.backend.name, subscription.id, 'documents', document.id)
        self._set_meta_info(store_prefix)
        self.storage.set(*store_prefix, 'object', to_dict(document))

        if not self.is_accepted_type(document):
            self.logger.info('%s document has no accepted type, no download', document)
            return

        template = self.get_backend_config('filename', default=self.default_filename)
        filename = formatter.format(
            template,
            subscription=subscription, document=document, extension=document.format,
        )
        path = self.root_path() / filename
        path.parent.mkdir(exist_ok=True)

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
        try:
            path.chmod(path.stat().st_mode & ~0o222)  # archiving, right?
        except OSError as exc:
            self.logger.warning('could not set file %r as readonly: %r', path, exc)
        self.app.print('Downloaded %s' % path)
        self.storage.set(*store_prefix, 'info', 'downloaded_at', datetime.datetime.now())

    def download_subscription(self, subscription):
        self.logger.debug('downloading subscription %s', subscription)

        store_prefix = ('db', self.backend.name, subscription.id, 'subscription')

        is_initial = bool(self.storage.get(*store_prefix, 'info', 'first_seen', default=None))
        self._set_meta_info(store_prefix)
        self.storage.set(*store_prefix, 'object', to_dict(subscription))

        # collect documents first, some backends do not support well mixing download and listing
        documents = []
        for document in self.backend.iter_documents(subscription):
            # TODO timezones?
            if document.date and to_datetime(document.date) < self.get_date_until(subscription, is_initial):
                self.logger.info('reached date threshold for %r', subscription)
                break

            documents.append(document)

        for document in documents:
            self.download_document(subscription, document)

    def download(self):
        self.app.print('Processing backend %r' % self.backend.name)
        self.root_path().mkdir(exist_ok=True)
        for subscription in self.backend.iter_subscription():
            self.download_subscription(subscription)


class BillDlApp(ReplApplication):
    APPNAME = 'billarchive'
    VERSION = __version__
    COPYRIGHT = 'Copyleft woob project'
    CAPS = (CapDocument,)
    STORAGE = {'db': {}}

    def do_download(self, _):
        """Download documents"""

        def download(backend):
            return BackendDownloader(backend, self).download()

        for _ in self._do_and_retry(download):
            pass

    def main(self, argv):
        self.load_config()
        self.create_storage()
        try:
            return super().main(argv)
        finally:
            self.storage.save()


if __name__ == '__main__':
    BillDlApp.run()
