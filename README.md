# billarchive

billarchive allows you to download bills from popular websites, so you don't
have to periodically visit every website where you buy products or services
and download bills.

It relies on modules implemented by [woob](https://woob.tech/modules).

[PyPI page](https://pypi.org/project/billarchive/)

## Configuration

The `~/.config/woob/backends` file must be configured for you to choose the
desired modules and their credentials.

Then `~/.config/woob/billarchive` can be configured to specify various
options, e.g. how to name downloaded files, whether to force conversion to pdf,
date until which new documents are searched, etc.

See [`config_example`](config_example) file in repository.

## Installation

### Normal setup

- pipx install billarchive

### Dev setup

You need to have pip installed first. You can look at [pip's manual](https://pip.pypa.io/en/stable/installation/) for more information.

#### If woob is already installed

```sh
git clone https://gitlab.com/hydrargyrum/billarchive/
cd billarchive
pip install --no-deps -e .
```

#### If woob is not installed already

```sh
git clone https://gitlab.com/hydrargyrum/billarchive/
cd billarchive
pip install -e .
```

## Usage

Run `billarchive download` to download all documents on all backends, as
specified by config.

Or run `billarchive -b backend download` to use only one backend at a time.

