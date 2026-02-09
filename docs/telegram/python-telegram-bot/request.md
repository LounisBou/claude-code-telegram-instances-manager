# Request

> HTTP transport layer for communicating with the Telegram Bot API -- timeouts, proxies, connection pools, and HTTP/2.

## Overview

The request module handles all HTTP communication between the bot and the Telegram API servers. The default implementation uses `httpx.AsyncClient`. In most cases, you configure request settings via `ApplicationBuilder` methods rather than instantiating request objects directly. Direct instantiation is only needed for advanced use cases like custom HTTP backends.

## Quick Usage

```python
from telegram.ext import Application

# Configure via ApplicationBuilder (preferred)
app = (
    Application.builder()
    .token("BOT_TOKEN")
    .read_timeout(10.0)
    .connect_timeout(10.0)
    .proxy("http://proxy.example.com:8080")
    .http_version("2")
    .build()
)
```

## Key Classes

### BaseRequest (abstract)

> Abstract interface for HTTP request implementations. Subclass this to use a different HTTP library.

**Methods to implement (all async):**

| Method | Returns | Description |
|---|---|---|
| `initialize()` | `None` | Set up the HTTP client. Called on application startup. |
| `shutdown()` | `None` | Close the HTTP client. Called on application shutdown. |
| `do_request(url, method, request_data, read_timeout, write_timeout, connect_timeout, pool_timeout)` | `tuple[int, bytes]` | Execute an HTTP request. Returns `(status_code, response_body)`. |

**`do_request` parameters:**

- `url` -- `str`, the full API URL.
- `method` -- `str`, HTTP method (`"GET"` or `"POST"`).
- `request_data` -- `RequestData | None`, contains parameters and files for the request.
- `read_timeout` -- `float | None`, seconds to wait for response data.
- `write_timeout` -- `float | None`, seconds to wait for sending data.
- `connect_timeout` -- `float | None`, seconds to wait for connection establishment.
- `pool_timeout` -- `float | None`, seconds to wait for a connection from the pool.

---

### HTTPXRequest

> Default request implementation using `httpx.AsyncClient`.

**Constructor:**

```python
HTTPXRequest(
    connection_pool_size: int = 256,
    read_timeout: float | None = 5.0,
    write_timeout: float | None = 5.0,
    connect_timeout: float | None = 5.0,
    pool_timeout: float | None = 1.0,
    http_version: str = "1.1",
    socket_options: tuple | None = None,
    proxy: str | httpx.Proxy | httpx.URL | None = None,
    media_write_timeout: float | None = 20.0,
    httpx_kwargs: dict | None = None,
)
```

| Param | Type | Default | Description |
|---|---|---|---|
| `connection_pool_size` | `int` | `256` | Maximum number of concurrent connections in the pool. |
| `read_timeout` | `float \| None` | `5.0` | Default seconds to wait for response data. `None` for no limit. |
| `write_timeout` | `float \| None` | `5.0` | Default seconds to wait for sending request data. `None` for no limit. |
| `connect_timeout` | `float \| None` | `5.0` | Default seconds to wait for TCP connection. `None` for no limit. |
| `pool_timeout` | `float \| None` | `1.0` | Seconds to wait for a connection from the pool when all are in use. `None` for no limit. |
| `http_version` | `str` | `"1.1"` | HTTP version: `"1.1"` or `"2"`. HTTP/2 requires `pip install httpx[http2]`. |
| `socket_options` | `tuple \| None` | `None` | Low-level socket options passed to the transport. |
| `proxy` | `str \| httpx.Proxy \| httpx.URL \| None` | `None` | Proxy URL. Supports HTTP and SOCKS proxies. |
| `media_write_timeout` | `float \| None` | `20.0` | Write timeout specifically for media uploads (photos, videos, documents). Higher than `write_timeout` because uploads are slower. |
| `httpx_kwargs` | `dict \| None` | `None` | Extra keyword arguments passed directly to `httpx.AsyncClient()`. Use for advanced httpx configuration. |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `async initialize()` | `None` | Creates the `httpx.AsyncClient` with configured settings. |
| `async shutdown()` | `None` | Closes the `httpx.AsyncClient`. |
| `async do_request(url, method, request_data, read_timeout, write_timeout, connect_timeout, pool_timeout)` | `tuple[int, bytes]` | Executes the HTTP request and returns `(status_code, response_body)`. |

## Common Patterns

### Configure via ApplicationBuilder (preferred)

```python
from telegram.ext import Application

app = (
    Application.builder()
    .token("BOT_TOKEN")
    .proxy("http://proxy.example.com:8080")
    .read_timeout(10.0)
    .write_timeout(10.0)
    .connect_timeout(10.0)
    .pool_timeout(5.0)
    .media_write_timeout(30.0)
    .connection_pool_size(512)
    .http_version("2")
    .build()
)
```

### Separate configuration for getUpdates

```python
from telegram.ext import Application

# Long polling uses a separate request instance with a longer read timeout
app = (
    Application.builder()
    .token("BOT_TOKEN")
    .read_timeout(5.0)                    # for regular API calls
    .get_updates_read_timeout(30.0)        # longer timeout for long polling
    .get_updates_proxy("socks5://proxy:1080")  # separate proxy for polling
    .build()
)
```

### Direct HTTPXRequest instantiation (advanced)

```python
from telegram.ext import Application
from telegram.request import HTTPXRequest

request = HTTPXRequest(
    connection_pool_size=512,
    read_timeout=10.0,
    proxy="http://proxy:8080",
    httpx_kwargs={"verify": "/path/to/cert.pem"},
)

app = (
    Application.builder()
    .token("BOT_TOKEN")
    .request(request)
    .build()
)
```

## Related

- [Application](application.md) -- ApplicationBuilder networking methods
- [Rate Limiting](rate-limiting.md) -- throttling outgoing requests
- [Errors](errors.md) -- NetworkError, TimedOut exceptions
