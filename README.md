# billarchive

billarchive allows you to download bills from popular websites, so you don't
have to periodically visit every website where you buy products or services
and download bills.

It relies on modules implemented by [weboob](https://weboob.org/modules).

# Configuration

The `~/.config/weboob/backends` file must be configured for you to choose the
desired modules and their credentials.

Then `~/.config/weboob/billarchive` can be configured to specify various
options, e.g. how to name downloaded files, whether to force conversion to pdf,
date until which new documents are searched, etc.

See `config_sample` file in repository.

# Usage

Run `billarchive download` to download all documents on all backends, as
specified by config.

Or run `billarchive -b backend download` to use only one backend at a time.

