Changelog
=========

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.3.6] - 2021-04-12

### Added
- Python 3.9 support.

### Changed
- `LNURL_STRICT_RFC3986` environment variable is now `False` (0) by default.
- Moved library to the LNbits family.

## [0.3.5] - 2020-08-18

### Added
- Option to ignore SSL certificate verification for HTTPS requests, in `handle()` and `get()`.

## [0.3.4] - 2020-08-04

### Fixed
- Port is not ignored anymore by `Url.base`.

### Changed
- `TorUrl` and `WebUrl` are now `OnionUrl` and `ClearnetUrl`, following LNURL spec terminology.

### Removed
- `LNURL_FORCE_SSL` environment variable is not used anymore. Only https is allowed now for `ClearnetUrl`s.

## [0.3.3] - 2020-02-18

### Added
- Support for `.onion` Tor URLs without SSL certificate (both http and https are valid for `TorUrl`).

### Fixed
- `__repr__` mixin.

## [0.3.2] - 2020-01-31

### Added
- Custom exception when `lnurl.get()` request fails.

### Fixed
- `LNURL_FORCE_SSL` and `LNURL_STRICT_RFC3986` environment variables are `True` when value is `"1"`.

## [0.3.1] - 2019-12-19

### Fixed
- Stupid import error for `Literal` in Python 3.8 :(

## [0.3.0] - 2019-12-19

### Added
- Changelog.
- New LNURL-pay metadata mime types for images.
- New `LnurlPayMetadata` properties: `.images` (_list_) and `.text` (_str_).
- `LnurlPayMetadata` now checks if the required "text/plain" entry exists.
- `LNURL_FORCE_SSL` and `LNURL_STRICT_RFC3986` environment variables.

### Changed
- For `LnurlPayMetadata` there is no `.list` property anymore: use `.list()` method instead.
- Hashed metadata should be accessed now with `LnurlPayResponse().metadata.h` instead of `LnurlPayResponse().h`
- `HttpsUrl` type is now called `Url`.
- `Url` is not valid when control characters are found or if it is not RFC3986 compliant.

### Fixed
- Fix `Url` type tests.
- Install `typing-extensions` only if Python version < 3.8.

## [0.2.0] - 2019-12-14

### Added
- Extra documentation in README.
- Full validation of LNURL responses using `pydantic` models.
- `.json()` and `.dict()` methods to export data from responses. Data is exported in camelCase
  by default, but internally all properties are still pythonic (snake_case).
- `LnurlResponse.from_dict()` helper to parse a response and assign the right type.
- `handle()` function to get a typed response directly from a LNURL if you have `requests` installed.
- Typed returns for `encode()` and `decode()` functions.
- `black` for code formating.

### Changed
- Responses now require that you pass kwargs instead of a dictionary: use `LnurlResponseModel(**dict)`
  instead of the previous `LnurlResponse(dict)`
- `HttpsUrl` uses default `pydantic` validations now.

## [0.1.1] - 2019-12-04

### Added
- Get URL checks back into `validate_url()` function (from 0.0.2).

### Changed
- We can now parse error responses in lowercase (even if this is not in the spec).

## [0.1.0] - 2019-11-24

### Added
- API documentation in README.
- `Lnurl` class and different `LnurlResponse` classes.
- New folder structure.
- Tests.

## [0.0.2] - 2019-11-21

### Removed
- Remove all duplicated code from `bech32` package. We import the package instead.

## [0.0.1] - 2019-11-14

### Added
- Initial commit, based on `bech32` package.
- `encode()` and `decode()` functions.


[unreleased]: https://github.com/lnbits/lnurl/compare/0.3.6...HEAD
[0.3.6]: https://github.com/lnbits/lnurl/compare/0.3.5...0.3.6
[0.3.5]: https://github.com/lnbits/lnurl/compare/0.3.4...0.3.5
[0.3.4]: https://github.com/lnbits/lnurl/compare/0.3.3...0.3.4
[0.3.3]: https://github.com/lnbits/lnurl/compare/0.3.2...0.3.3
[0.3.2]: https://github.com/lnbits/lnurl/compare/0.3.1...0.3.2
[0.3.1]: https://github.com/lnbits/lnurl/compare/0.3.0...0.3.1
[0.3.0]: https://github.com/lnbits/lnurl/compare/0.2.0...0.3.0
[0.2.0]: https://github.com/lnbits/lnurl/compare/0.1.1...0.2.0
[0.1.1]: https://github.com/lnbits/lnurl/compare/0.1.0...0.1.1
[0.1.0]: https://github.com/lnbits/lnurl/compare/0.0.2...0.1.0
[0.0.2]: https://github.com/lnbits/lnurl/compare/0.0.1...0.0.2
[0.0.1]: https://github.com/lnbits/lnurl/releases/tag/0.0.1
