from collections import namedtuple
import functools
import asyncio
import concurrent
import json
import base64
import rx
import rx.operators as ops
from rx.subject import Subject

import cyclotron_aiohttp.http as http


Api = namedtuple('Api', ['read_key', 'watch_key'])
Adapter = namedtuple('Adapter', ['sink', 'api'])

KeyValue = namedtuple('KeyValue', ['key', 'value'])
KV_PATH = 'v1/kv'


def _on_subscribe(post_action):
    def _on_subscribe(source):
        def subscribe(observer, scheduler):
            disposable = source.subscribe(observer, scheduler=scheduler)
            post_action()
            return disposable
        return rx.create(subscribe)

    return _on_subscribe


def _retry_on_timeout(index):
    def __retry_on_timeout(source):
        def on_subscribe(observer, scheduler):
            disposable = None

            def dispose():
                if disposable is not None:
                    disposable.dispose()

            def on_error(e):
                nonlocal disposable
                print("received error: {}".format(e))
                print(type(e))
                print(isinstance(e, asyncio.TimeoutError))
                print(isinstance(e, concurrent.futures._base.TimeoutError))
                if index and isinstance(e, asyncio.TimeoutError):
                    print("received timeout")
                    disposable.dispose()
                    disposable = source.subscribe(
                        on_next=observer.on_next,
                        on_error=on_error,
                        on_completed=observer.on_completed,
                    )
                else:
                    observer.on_error(e)

            disposable = source.subscribe(
                on_next=observer.on_next,
                on_error=on_error,
                on_completed=observer.on_completed,
            )
            return dispose
        return rx.create(on_subscribe)
    return __retry_on_timeout


def read_key(http_client, endpoint, key):
    '''Reads a key on the specified endpoint

    Args:
        http_client: An instance of http client. This parameter is already
            binded when called from the adapter.
        endpoint: the consul server full url
        key: The key to read

    Returns:
        On observable that emits a single KeyValue item if the request
        succeeds. Otherwise the observable completes on error.

    Example:
        >>>import cyclotron_consul.kv as kv
        >>>client = kv.client(http_source)
        >>>client.api.read_key("http://localhost:8500", "mykey").subscribe(
        >>>    on_next=print
        >>>)
        >>># forward client.sink to http driver sink
    '''
    method = "GET"
    url = '{}/{}/{}'.format(endpoint, KV_PATH, key)
    return http_client.api.request(method, url).pipe(
        ops.map(lambda i: i.data),
        ops.map(json.loads),
        ops.map(lambda i: KeyValue(
            key=i[0]['Key'],
            value=base64.b64decode(i[0]['Value']).decode('utf-8')
        )),
    )


def watch_key(http_client, endpoint, key):
    '''Reads a key on the specified endpoint, and watch for updates.

    Args:
        http_client: An instance of http client. This parameter is already
            binded when called from the adapter.
        endpoint: the consul server full url
        key: The key to read

    Returns:
        On observable that emits a KeyValue item each time the value
        associated to the key is updated on consul. In case of error,
        the observable completes on error.

    Example:
        >>>import cyclotron_consul.kv as kv
        >>>client = kv.client(http_source)
        >>>client.api.watch_key("http://localhost:8500", "mykey").subscribe(
        >>>    on_next=print
        >>>)
        >>># forward client.sink to http driver sink
    '''
    method = "GET"
    url = '{}/{}/{}'.format(endpoint, KV_PATH, key)

    feedback = Subject()

    def connect(): reponse_feedback.subscribe(feedback)

    init = rx.merge(feedback, rx.just(None))
    response = init.pipe(
        _on_subscribe(connect),
        ops.flat_map(lambda i: http_client.api.request(
            method,
            "{}{}".format(url, "?index={}".format(i) if i else "")).pipe(
                _retry_on_timeout(i),
            )
        ),
        ops.map(lambda i: i.data.decode('utf-8')),
        ops.map(json.loads),
        ops.share(),
    )

    reponse_feedback = response.pipe(
        ops.map(lambda i: i[0]['ModifyIndex'])
    )

    key_value = response.pipe(
        ops.map(lambda i: KeyValue(
            key=i[0]['Key'],
            value=base64.b64decode(i[0]['Value']).decode('utf-8')
        )),
    )

    return key_value


def adapter(source):
    '''Creates a consul adapter for the KV API.

    Args:
        source: an aiohttp response stream.

    Returns:
        A Client object
    '''
    http_client = http.client(http.ClientSource(source))

    return Adapter(
        sink=http_client.sink.http_request,
        api=Api(
            read_key=functools.partial(read_key, http_client),
            watch_key=functools.partial(watch_key, http_client),
        )
    )
