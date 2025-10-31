"""Test HTTP server helper for integration testing.

This module provides a simple HTTP server that can be used in tests
to simulate external services or provide controlled responses.

Example:
    >>> with httpserver("localhost", 8080, "Hello World") as server:
    ...     # Server is running, make requests to localhost:8080
    ...     response = requests.get("http://localhost:8080")
    ...     assert response.text == "Hello World"
    # Server automatically shuts down when exiting context
"""

"""Test HTTP server helper for integration testing.

This module provides a simple HTTP server that can be used in tests
to simulate external services or provide controlled responses.

Example:
    >>> with httpserver("localhost", 8080, "Hello World") as server:
    ...     # Server is running, make requests to localhost:8080
    ...     response = requests.get("http://localhost:8080")
    ...     assert response.text == "Hello World"
    # Server automatically shuts down when exiting context
"""

import http.server
import socketserver
import threading
import os
import time
from typing import Optional


class httpserver:
    """
    A lightweight HTTP server for testing purposes.

    This server can be configured to return custom content and simulate
    delays or timeouts, making it useful for testing HTTP client behavior
    under various conditions.

    Attributes:
        host (str): Server hostname or IP address
        port (int): Server port number
        content (str): Content to return for all GET requests
        timeout (Optional[float]): Delay in seconds before responding

    Example:
        >>> # Basic server
        >>> server = httpserver("localhost", 8080, "Test content")
        >>> server.serve()
        >>> # ... make requests ...
        >>> server.shutdown()

        >>> # Context manager (recommended)
        >>> with httpserver("localhost", 8080, "Test", timeout=2) as server:
        ...     # Server responds after 2 second delay
        ...     pass  # Server automatically shuts down
    """

    def __init__(self, host: str, port: int, content: str = "", timeout: Optional[float] = None):
        """
        Initialize the test HTTP server.

        Args:
            host: Hostname or IP address to bind to (e.g., "localhost", "127.0.0.1")
            port: Port number to listen on (e.g., 8080)
            content: Content to return for all GET requests (default: empty string)
            timeout: Optional delay in seconds before responding to requests
                   (useful for testing timeout handling)

        Example:
            >>> server = httpserver("localhost", 8080, "<html>Test</html>")
            >>> server = httpserver("127.0.0.1", 9000, timeout=5.0)  # 5s delay
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.content = content
        self._server = None
        self._thread = None

    def serve(self):
        """
        Start the HTTP server in a background thread.

        Creates and starts the server, making it ready to accept connections.
        The server runs in a daemon thread, so it won't prevent the main
        program from exiting.

        Returns:
            self: Returns self for method chaining

        Raises:
            OSError: If the port is already in use or binding fails

        Example:
            >>> server = httpserver("localhost", 8080, "Hello")
            >>> server.serve()  # Server is now running
            >>> # ... do testing ...
            >>> server.shutdown()  # Clean shutdown
        """
        this = self

        class MyRequestHandler(http.server.SimpleHTTPRequestHandler):
            """Custom request handler that returns configured content."""

            def _set_headers(self):
                """Set standard HTTP response headers."""
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

            def do_GET(self):
                """Handle GET requests by returning configured content with optional delay."""
                if this.timeout is not None:
                    time.sleep(this.timeout)
                self._set_headers()
                self.wfile.write(this.content.encode("utf-8"))

        Handler = MyRequestHandler

        self._server = socketserver.TCPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()

        return self

    def shutdown(self):
        """
        Shutdown the HTTP server and clean up resources.

        Stops the server and waits for the background thread to terminate.
        This method is safe to call multiple times.

        Example:
            >>> server = httpserver("localhost", 8080).serve()
            >>> # ... use server ...
            >>> server.shutdown()  # Clean shutdown
        """
        if self._server:
            self._server.shutdown()
        if self._thread:
            self._thread.join()

    def __enter__(self):
        """
        Context manager entry point - start the server.

        Returns:
            self: The running server instance

        Example:
            >>> with httpserver("localhost", 8080, "content") as server:
            ...     # Server is running and ready for requests
            ...     pass  # Server will auto-shutdown on exit
        """
        return self.serve()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point - shutdown the server.

        Args:
            exc_type: Exception type (if any occurred in with block)
            exc_val: Exception value (if any occurred in with block)
            exc_tb: Exception traceback (if any occurred in with block)

        Note:
            Performs clean shutdown regardless of whether an exception occurred
            in the with block.
        """
from typing import Optional
    """
    A lightweight HTTP server for testing purposes.
    
    This server can be configured to return custom content and simulate
    delays or timeouts, making it useful for testing HTTP client behavior
    under various conditions.
    
    Attributes:
        host (str): Server hostname or IP address
        port (int): Server port number
        content (str): Content to return for all GET requests
        timeout (Optional[float]): Delay in seconds before responding
    
    Example:
        >>> # Basic server
        >>> server = httpserver("localhost", 8080, "Test content")
        >>> server.serve()
        >>> # ... make requests ...
        >>> server.shutdown()
        
        >>> # Context manager (recommended)
        >>> with httpserver("localhost", 8080, "Test", timeout=2) as server:
        ...     # Server responds after 2 second delay
        ...     pass  # Server automatically shuts down
    """
    def __init__(self, host: str, port: int, content: str = "", timeout: Optional[float] = None):
        """
        Initialize the test HTTP server.

        Args:
            host: Hostname or IP address to bind to (e.g., "localhost", "127.0.0.1")
            port: Port number to listen on (e.g., 8080)
            content: Content to return for all GET requests (default: empty string)
            timeout: Optional delay in seconds before responding to requests
                   (useful for testing timeout handling)

        Example:
            >>> server = httpserver("localhost", 8080, "<html>Test</html>")
            >>> server = httpserver("127.0.0.1", 9000, timeout=5.0)  # 5s delay
        """
        """
        Start the HTTP server in a background thread.
        
        Creates and starts the server, making it ready to accept connections.
        The server runs in a daemon thread, so it won't prevent the main
        program from exiting.
        
        Returns:
            self: Returns self for method chaining
        
        Raises:
            OSError: If the port is already in use or binding fails
        
        Example:
            >>> server = httpserver("localhost", 8080, "Hello")
            >>> server.serve()  # Server is now running
            >>> # ... do testing ...
            >>> server.shutdown()  # Clean shutdown
        """
            """Custom request handler that returns configured content."""
                """Set standard HTTP response headers."""
                """Handle GET requests by returning configured content with optional delay."""
        """
        Shutdown the HTTP server and clean up resources.
        
        Stops the server and waits for the background thread to terminate.
        This method is safe to call multiple times.
        
        Example:
            >>> server = httpserver("localhost", 8080).serve()
            >>> # ... use server ...
            >>> server.shutdown()  # Clean shutdown
        """
        """
        Context manager entry point - start the server.
        
        Returns:
            self: The running server instance
        
        Example:
            >>> with httpserver("localhost", 8080, "content") as server:
            ...     # Server is running and ready for requests
            ...     pass  # Server will auto-shutdown on exit
        """
        """
        Context manager exit point - shutdown the server.
        
        Args:
            exc_type: Exception type (if any occurred in with block)
            exc_val: Exception value (if any occurred in with block)  
            exc_tb: Exception traceback (if any occurred in with block)
        
        Note:
            Performs clean shutdown regardless of whether an exception occurred
            in the with block.
        """
        self._server.shutdown()
        self._server.server_close()
