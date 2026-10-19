# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Bridge between the synchronous Odoo worker and the asynchronous brbank.

Every call to the bank goes through `run_in_dedicated_loop`: the coroutine runs
in a short-lived thread with its own event loop, created and closed by
`asyncio.run`. Nothing of the loop survives the call, so no loop leaks between
requests, crons or workers (prefork, threaded or gevent), and a loop already
running in the calling thread (gevent, tests) does not get in the way.

The coroutine must not touch the Odoo environment: everything it needs is read
before, in the calling thread, and passed as plain data.
"""

import asyncio
import threading


def run_in_dedicated_loop(coroutine_factory):
    """Run `coroutine_factory()` to completion in a dedicated event loop.

    :param coroutine_factory: A callable without arguments returning the
        coroutine to run. It is called inside the dedicated thread, so the
        coroutine, its HTTP client and its sockets are bound to that loop.
    :return: What the coroutine returns.
    :raise: What the coroutine raises, unchanged.
    """
    outcome = {}

    def target():
        try:
            outcome["result"] = asyncio.run(coroutine_factory())
        except BaseException as error:  # pylint: disable=broad-except
            outcome["error"] = error

    worker = threading.Thread(target=target, name="brbank-call", daemon=True)
    worker.start()
    worker.join()
    if "error" in outcome:
        raise outcome["error"]
    return outcome.get("result")
