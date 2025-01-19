import http.client as httplib
import base64
import json
import urllib.parse as urlparse
import time

class BitcoinRpcClient:
    """Bitcoin Core RPC client with automatic reconnection.
    
    Usage:
    client = BitcoinRpcClient(user="myuser", password="mypass")
    block_count = client.getblockcount()
    """
    
    def __init__(self, user, password, host="localhost", port=8332, timeout=120, max_retries=10):
        """Initialize the Bitcoin client with connection parameters.
        
        Args:
            user (str): RPC username
            password (str): RPC password
            host (str, optional): Host address. Defaults to "localhost".
            port (int, optional): Port number. Defaults to 8332.
            timeout (int, optional): Connection timeout in seconds. Defaults to 120.
            max_retries (int, optional): Maximum number of retry attempts. Defaults to 10.
        """
        self.__timeout = timeout
        self.__max_retries = max_retries
        self.__url = urlparse.urlparse(f"http://{user}:{password}@{host}:{port}")
        authpair = f"{user}:{password}".encode('utf8')
        self.__auth_header = b'Basic ' + base64.b64encode(authpair)
        self.__setup_connection()
    
    def __setup_connection(self):
        """Create a new HTTP connection."""
        port = self.__url.port or 80
        conn_class = httplib.HTTPSConnection if self.__url.scheme == 'https' else httplib.HTTPConnection
        self.connection = conn_class(self.__url.hostname, port, timeout=self.__timeout)
    
    def __getattr__(self, name: str) -> callable:
        """Convert attribute access into RPC calls with automatic reconnection.
        Args:
            name (str): The name of the RPC method to call
        Returns:
            callable: A function that executes the RPC call with retry logic
        Raises:
            AttributeError: If the name is a Python special method
            Exception: If the RPC call fails after all retries
        """
        if name.startswith('__') and name.endswith('__'):
            raise AttributeError
        
        name = name.lower()
        
        def caller(*args):
            for attempt in range(self.__max_retries):
                try:
                    postdata = json.dumps({
                        'version': '1.1',
                        'method': name,
                        'params': args,
                        'id': 1
                    })
                    self.connection.request('POST', self.__url.path, postdata, {
                        'Host': self.__url.hostname,
                        'Authorization': self.__auth_header,
                        'Content-type': 'application/json'
                    })
                    self.connection.sock.settimeout(self.__timeout)
                    response = json.loads(self.connection.getresponse().read().decode('utf8'))
                    if response.get('error'):
                        raise Exception(response['error'].get('message', 'Unknown RPC error'))
                    
                    return response['result']
                    
                except (Exception) as e:
                    if attempt < self.__max_retries - 1:
                        time.sleep(1 * (attempt + 1))  # Progressive backoff
                        try:
                            self.connection.close()
                        except:
                            pass
                        self.__setup_connection()
                    continue
                    
            raise Exception(f"RPC call '{name}' failed after {self.__max_retries} attempts")
        
        return caller