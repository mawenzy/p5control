"""
Class which provides a thread responsible for callbacks such that they do not block other calls
to the data server.
"""
import logging
import threading
import queue
from multiprocessing.pool import ThreadPool
from subprocess import TimeoutExpired


from ..util import name_generator
from ..settings import CALLBACK_THREAD_COUNT

logger = logging.getLogger(__name__)

# unique id generator for callbacks
id_generator = name_generator(
    "id",
    width=4,
)
id_generator_lock = threading.Lock()

def get_callback_id():
    """Thread save id generator for unique callback ids."""
    with id_generator_lock:
        newid = next(id_generator)
    logger.debug('generated id "%s"', newid)
    return newid

class CallbackControllerError(Exception):
    """Exception related to the callback class."""

class CallbackController:
    """
    Controls the callback process to run independently and not block measurement threads.
    """
    def __init__(self) -> None:
        self.queue = queue.Queue()

        # callbacks for adding data to a dataset
        self._dset_callbacks = {}
        self._dset_callback_lock = threading.Lock()

        # callbacks for adding new elements below a group
        self._grp_callbacks = {}
        self._grp_callback_lock = threading.Lock()

        self._thread = None
        self.STOP_EVENT = threading.Event()

    def start(self):
        """
        Start callback thread and its associated thread pool. Will call all callbacks appended
        to the queue.
        """
        if self._thread:
            raise CallbackControllerError('Can\'t start because thread is already running.')

        self._thread = threading.Thread(
            target=self._callback_thread,
            args=[self.STOP_EVENT]
        )
        self._thread.start()

    def stop(self):
        """
        Stop callback thread
        """
        if not self._thread:
            raise CallbackControllerError('Can\'t stop because thread is not running.')

        self.STOP_EVENT.set()

        # removing callbacks
        logger.debug('removing all dataset callbacks')
        with self._dset_callback_lock:
            for key in self._dset_callbacks.copy():
                self._dset_callbacks.pop(key)

        logger.debug('removing all group callbacks')
        with self._grp_callback_lock:
            for key in self._grp_callbacks.copy():
                self._grp_callbacks.pop()

        # block until the thread is actually stopped
        self._thread.join()
        self._thread = None

    def _call_callback(self, path, data, is_group):
        if is_group:
            calls = []

            with self._grp_callback_lock:
                for (callid, (callpath, func)) in self._grp_callbacks.copy().items():
                    if path.startswith(callpath):
                        calls.append((callid, func))

            # call callbacks without locking the dictionary to improve performance
            for callid, func in calls:
                try:
                    logger.debug('calling group callback "%s" for "%s"', callid, path)
                    func(path)
                except (EOFError, TimeoutExpired):
                    logger.info('Can\'t connect to callback "%s", removing it.', callid)
                    self._grp_callbacks.pop(callid)

        else:
            calls = []

            with self._dset_callback_lock:
                for (callid, (callpath, func)) in self._dset_callbacks.items():
                    if callpath == path:
                        calls.append((callid, func))

            # call callbacks without locking the dictionary to improve performance
            for callid, func in calls:
                try:
                    logger.debug('calling callback "%s" for "%s"', callid, path)
                    func(data)
                except (EOFError, TimeoutExpired):
                    logger.info('Can\'t connect to callback "%s", removing it.', callid)
                    self.remove_callback(callid)

    def _callback_thread(
        self,
        stop_event: threading.Event,
        refresh_delay: float = 1,
    ):
        logger.info("callback thread started")
        pool = ThreadPool(CALLBACK_THREAD_COUNT)

        while not stop_event.is_set():

            try:
                args = self.queue.get(block=True, timeout=refresh_delay)
            except queue.Empty:
                continue
            else:
                pool.apply_async(self._call_callback, args=args)

        pool.close()
        pool.join()

        logger.info("callback thread stopped")

        # reset stop flag
        stop_event.clear()


    def register_callback(
        self,
        path: str,
        func,
        is_group: bool = False,
    ) -> None:
        """Add a callback to call when data is appended to the dataset at `path`,
        called with func(arr)

        Parameters
        ----------
        path : str
            path in the hdf5 file
        func : function(np.ndarray)
            function to call

        Returns
        -------
        id : str
            unique id to identify this callback and be able to remove it
        """
        callid = get_callback_id()

        if is_group:
            logger.info('registering callback "%s" for group: "%s"', callid, path)
            with self._grp_callback_lock:
                self._grp_callbacks[callid] = (path, func)
        else:
            logger.info('registering callback "%s" for dataset: "%s"', callid , path)
            with self._dset_callback_lock:
                self._dset_callbacks[callid] = (path, func)

        return callid

    def remove_callback(
        self,
        callid: str,
    ):
        """remove callback specified by ``id``.

        Raises
        ------
        KeyError
            if there exists no callback with ``id``
        """
        with self._dset_callback_lock:
            if callid in self._dset_callbacks:
                logger.info('removing callback "%s"', callid)
                self._dset_callbacks.pop(callid)
                return

        with self._grp_callback_lock:
            if callid in self._grp_callbacks:
                logger.info('removing callback "%s"', callid)
                self._grp_callbacks.pop(callid)
                return

        logger.info('callback with id "%s" not found, skipping...', callid)
