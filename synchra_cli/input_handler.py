import asyncio
import sys
import threading

class AsyncInput:
    """Helper to read from stdin asynchronously using a daemon thread to prevent exit hangs."""
    
    def __init__(self):
        self.queue = asyncio.Queue()
        self._loop = asyncio.get_event_loop()
        self._stop_event = threading.Event()
        self._thread = None

    def _read_loop(self):
        """Monitor stdin in a separate thread."""
        while not self._stop_event.is_set():
            # This is blocking, but it's okay because it's a daemon thread
            line = sys.stdin.readline()
            if line:
                # Use call_soon_threadsafe to put into the async queue
                self._loop.call_soon_threadsafe(self.queue.put_nowait, line.strip())
            else:
                # EOF
                break

    async def start(self):
        """Starts the daemon thread to read from stdin."""
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal the stop event for completeness (though it won't unblock readline)."""
        self._stop_event.set()

    async def get(self) -> str:
        """Returns the next line from the queue."""
        return await self.queue.get()
