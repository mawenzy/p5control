from rpyc import async_

def wait(
    callable_netref,
    *args,
    timeout : float = None,
    **kwargs
):
    """
    Calls `callable_netref` with `*args` and `**kwargs` and waits as long as required for it to
    answer. Use this function when your results expire. By default, `rpyc` has a 30s timeout for
    all requests, which is ignored in this function.

    Parameters
    ----------
    callable_netref : callable
        netref which is callable
    timeout : float = None
        timeout for the async result
    *args, **kwarsg
        arguments provided to callable_netref  
    """
    async_fun = async_(callable_netref)
    async_res = async_fun(*args, **kwargs)

    if timeout:
        async_res.set_expiry(timeout)

    async_res.wait()
    return async_res.value
