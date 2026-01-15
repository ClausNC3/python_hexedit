"""Various utility functions.

License:
    MIT License

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
"""
import mmap
import os
import queue
import inspect
import enum
import threading

from collections.abc import Iterable
from typing import Callable, Generator, List, Any, Optional, Tuple

def memory_map(filename: str, access=mmap.ACCESS_READ) -> mmap.mmap:
    """Map a file to the memory using mmap.

    Args:
        filename:
            Path to file to be mapped.
        access:
            Access type.

    Returns:
        Memory mapped object.
    """
    size = os.path.getsize(filename)
    fd = os.open(filename, os.O_RDONLY if access == mmap.ACCESS_READ else os.O_RDWR)
    try:
        return mmap.mmap(fd, size, access=access)
    finally:
        # Close the file descriptor after creating the mmap
        # The mmap retains its own reference to the file
        os.close(fd)

def chunker(seq: Iterable, size: int) -> Generator[List, None, None]:
    """Divide iterable into chunks of given size.

    The returned generator will return chunks of requested size, except
    for the last chunk which might be smaller.

    Args:
        seq:
            Iterable to divide to chunks.
        size:
            Size of each chunk.
    
    Returns:
        Generator for chunks of the requested size.
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def getproperties(obj):
    """Generator for properties of an object."""
    t = obj.__class__
    for tp in inspect.getmro(t):
        for name, value in vars(tp).items():
            if isinstance(value, property):
                yield name, getattr(obj, name)

def start_deamon(function: Callable, args: Iterable = ()) -> threading.Thread:
    """Start a deamon with the given function and arguments."""
    thread = threading.Thread(target = function, args = args)
    thread.daemon = True
    thread.start()
    return thread

class BackgroundTasks():
    """A class to track background operations."""

    class State(enum.Enum):
        STARTED     = enum.auto()
        FAILED      = enum.auto()
        SUCCEEDED   = enum.auto()

    def __init__(self) -> None:
        self.tasks = {}

    def start_task(self, task: Any) -> None:
        """Mark a task as started.
        
        Args:
            task:
                Identifier for the task.
        """
        if task in self.tasks:
            raise RuntimeError(f"Task {task} already started")
        self.tasks[task] = self.State.STARTED

    def task_done(self, task: Any, is_success: bool) -> None:
        """Mark a task as done.
        
        Args:
            is_success:
                True if task was successful, False otherwise
        """
        self.tasks[task] = self.State.SUCCEEDED if is_success else self.State.FAILED

    def all_done(self) -> bool:
        """Returns True if all tasks were completed."""
        return all([x != self.State.STARTED for x in self.tasks.values()])

    def all_succeeded(self) -> bool:
        """Returns True if all tasks were completed successfully."""
        return all([x == self.State.SUCCEEDED for x in self.tasks.values()])

class WorkItem(object):
    """Class to offload jobs to a worker thread."""
    def __init__(self) -> None:
        start_deamon(self._working_thread)
        
    def _working_thread(self) -> None:
        """The worker thread. Takes jobs from the input queue and sends the result to the output queue."""
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        while True:
            queue_item = self.input_queue.get(block = True)
            if queue_item is None:
                return

            handle, function, args = queue_item
            result = function(*args)

            self.output_queue.put((handle, result))

    def submit_job(self, handle: Any, work_function: Callable, work_args: Tuple) -> None:
        """Submit a job to the work-item.
        
        Args:
            handle:
                Unique handle to identify job.
            work_function:
                Function to perform the work.
            work_args:
                Arguments for the work function.
        """
        self.input_queue.put((handle, work_function, work_args))

    def get_done_job(self) -> Tuple[Any, Any]:
        """Returns a tuple of (handle, result) if a job is done, or None otherwise."""
        try:
            return self.output_queue.get(block = False)
        except queue.Empty:
            return None

    def stop(self):
        """Stop the working thread."""
        self.input_queue.put(None)