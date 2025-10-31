# ultra_simple_worker.py
import threading
import queue
import time
import logging
import sys
import os

# Set up logging for this module
# Add parent directories to path to import from scaffold
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from scaffold import setup_module_logger
    logger = setup_module_logger(__name__)
except ImportError:
    # Fallback to standard logging if scaffold is not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class WorkerGovernor:
    """
    A simple background worker system that processes jobs in separate threads.
    """

    def __init__(self, num_workers=3):
        """
        Initialize the governor with a specified number of workers.

        Args:
            num_workers: How many worker threads to create (default: 3)
        """
        self.num_workers = num_workers
        self.job_queue = queue.Queue()  # Thread-safe queue to hold jobs
        self.workers = []  # List to track worker threads
        self.running = False  # Flag to control worker lifecycle
        self.jobs_done = 0  # Simple counter for completed jobs
        self.lock = threading.Lock()  # Prevents race conditions on the counter

    @classmethod
    def started(cls, num_workers: int = 3):
        governor = WorkerGovernor(num_workers=num_workers)
        governor.start()
        return governor

    def start(self):
        """
        Start all worker threads.

        Each worker runs in the background, constantly checking for new jobs.
        """
        self.running = True

        # Create and start each worker thread
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker,  # The function each worker will run
                args=(i,),  # Pass worker ID as argument
                daemon=True  # Dies when main program exits
            )
            worker.start()
            self.workers.append(worker)

        logger.info("Started %d workers", self.num_workers)

    def add_job(self, func, *args, **kwargs):
        """
        Add a job to the queue for workers to process.

        Args:
            func: The function to call (like shout_music)
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Example:
            governor.add_job(shout_music, "Beatles", "Abbey Road")
        """
        # Package the function and its arguments into a simple tuple
        job = (func, args, kwargs)

        # Put the job in the queue - workers will pick it up automatically
        self.job_queue.put(job)

    def _worker(self, worker_id):
        """
        The main worker loop - this runs in each worker thread.

        Workers continuously:
        1. Wait for a job from the queue
        2. Execute the job
        3. Update the completion counter
        4. Repeat until told to stop

        Args:
            worker_id: Unique identifier for this worker (for logging)
        """
        while self.running:
            try:
                # Wait up to 1 second for a job - prevents infinite blocking
                job = self.job_queue.get(timeout=1)

                if job is None:  # Special "poison pill" signal to stop
                    break

                # Unpack the job tuple
                func, args, kwargs = job

                logger.debug("Worker %d starting job...", worker_id)

                try:
                    # Execute the actual job function
                    func(*args, **kwargs)

                    # Safely increment the completion counter
                    with self.lock:
                        self.jobs_done += 1

                except Exception as e:
                    # Don't crash the worker if a job fails
                    logger.error("Job failed: %s", e)

                # Tell the queue this job is finished
                self.job_queue.task_done()

            except queue.Empty:
                # No jobs available right now - just continue looping
                continue

    def wait_for_completion(self):
        """
        Block until all jobs in the queue are finished.

        This is useful when you want to wait for all work to be done
        before proceeding or shutting down.
        """
        self.job_queue.join()

    def stop(self):
        """
        Gracefully stop all workers.

        Sends a "poison pill" (None) to each worker to signal shutdown.
        """
        self.running = False

        # Send stop signals to wake up all workers
        for _ in range(self.num_workers):
            self.job_queue.put(None)

    def status(self):
        """
        Get current status information.

        Returns:
            Dictionary with current stats
        """
        with self.lock:
            return {
                'jobs_completed': self.jobs_done,
                'jobs_waiting': self.job_queue.qsize(),
                'workers': self.num_workers,
                'running': self.running
            }


def shout_music(artist, album):
    """
    A fun example job that shouts about music!

    This demonstrates how any function can be used as a job.
    The worker system doesn't care what the job does - it just calls it.

    Args:
        artist: Name of the musical artist
        album: Name of the album
    """
    message = f"SHOUTING: I LISTEN TO {artist.upper()}'S ALBUM {album.upper()}"
    logger.info("🎵 %s", message)

    # Simulate some work being done
    time.sleep(0.5)

    return message


# This is the "main guard" - code that only runs when script is executed directly
if __name__ == '__main__':
    """
    Main guard block demonstration.

    This code only runs when you execute: python ultra_simple_worker.py
    It does NOT run when another script imports this module.

    Perfect for:
    - Demonstrating how to use your code
    - Running tests
    - Providing examples
    - Command-line interfaces
    """

    logger.info("🎸 Ultra-Simple Worker Governor Demo 🎸")
    logger.info("=" * 45)

    # Step 1: Create the governor with 2 workers
    logger.info("\n📋 Step 1: Creating governor...")
    # governor: WorkerGovernor = WorkerGovernor(num_workers=2)
    governor = WorkerGovernor.started(num_workers=2)

    # Step 2: Add some jobs
    logger.info("\n🎼 Step 3: Adding (music) jobs...")

    # Each of these will be processed by available workers
    albums = [
        ("The Beatles", "Abbey Road"),
        ("Pink Floyd", "The Wall"),
        ("Led Zeppelin", "IV"),
        ("Queen", "News of the World"),
        ("Nirvana", "Nevermind")
    ]

    for artist, album in albums:
        governor.add_job(shout_music, artist, album)
        logger.info("   ➕ Added: %s - %s", artist, album)

    # Step 4: Wait for all jobs to complete
    logger.info("\n⏳ Step 4: Processing %d albums...", len(albums))
    governor.wait_for_completion()

    # Step 5: Show final results
    logger.info("\n📊 Step 5: Final results...")
    final_status = governor.status()
    logger.info("   ✅ Jobs completed: %d", final_status['jobs_completed'])
    logger.info("   📦 Jobs waiting: %d", final_status['jobs_waiting'])
    logger.info("   👷 Workers: %d", final_status['workers'])

    # Step 6: Clean shutdown
    logger.info("\n🛑 Step 6: Shutting down...")
    governor.stop()

    logger.info("\n🎤 Demo complete! Rock on! 🤘")
    logger.info("\nTo use this as a module:")
    logger.info(">>> from ultra_simple_worker import WorkerGovernor, shout_music")
    logger.info(">>> gov = WorkerGovernor()")
    logger.info(">>> gov.start()")
    logger.info(">>> gov.add_job(shout_music, 'Beatles', 'Abbey Road')")
