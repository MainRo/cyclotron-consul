from collections import namedtuple

import rx
import rx.operators as ops

from cyclotron import Component
from cyclotron.asyncio.runner import run
import cyclotron_aiohttp.http as http
import cyclotron_std.sys.stdout as stdout

import cyclotron_consul.kv as kv

ReadKeySource = namedtuple('ReadKeySource', ['http'])
ReadKeySink = namedtuple('ReadKeySink', ['http', 'stdout'])
ReadKeyDrivers = namedtuple('ReadKeyDrivers', ['http', 'stdout'])


def read_key(source):
    kv_adapter = kv.adapter(source.http.response)

    value = kv_adapter.api.watch_key("http://localhost:8500", "test").pipe(
        ops.map(lambda i: "key: {}, value: {}".format(i.key, i.value)),
    )

    return ReadKeySink(
        http=http.Sink(request=kv_adapter.sink),
        stdout=stdout.Sink(data=value),
    )


def main():
    run(Component(call=read_key, input=ReadKeySource),
        ReadKeyDrivers(
            http=http.make_driver(),
            stdout=stdout.make_driver(),
        )
    )


if __name__ == '__main__':
    main()