Get Started
============

This packages exposes one adapter per consul API family.

KV Store
---------

One can Access the KV store with the kv adapter:

.. code: python

    import cyclotron_consul.kv as kv

    kv_adapter = kv.adapter(http_response)

The constructor of the kv adapter takes an observable of http_response as input,
and returns an Adapter object. The Adapter object contains two properties:

* sink: An observable of http requests (requests sent to the consul endpoint)
* api: An accessor to the KV Store APIs


Read the value of a key in the KV Store
........................................

Reading a key is done the following way:

.. code:: python

    import cyclotron_consul.kv as kv

    kv_adapter = kv.adapter(source.http.response)

    value = kv_adapter.api.read_key("http://localhost:8500", "test")

Where value is an observable that emits a single item with a Key/Value object.

Here is a full example:

.. code:: python

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

        value = kv_adapter.api.read_key("http://localhost:8500", "test").pipe(
            ops.map(lambda i: "key: {}, value: {}".format(i.key, i.value))
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


Watch the value of a key in the KV Store
........................................

This is similar to reading a key, except that the result observable emits a new
items each time the value of the key changes:

.. code:: python

    import cyclotron_consul.kv as kv

    kv_adapter = kv.adapter(source.http.response)

    value = kv_adapter.api.watch_key("http://localhost:8500", "test")

Where value is an observable that emits an item with a Key/Value object each
time the value of the key is updated on consul.

Here is a full example:

.. code:: python

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
