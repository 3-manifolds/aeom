from __future__ import print_function
import sys, os, socket, tempfile, shutil, multiprocessing, atexit, pickle
from .version import __version__

class Pending(object):
    """
    An object of this class is returned by Asynchronizer.compute if the
    worker has not finished its computation yet.
    """
    def __repr__(self):
        return '<Pending computation>'

pending = Pending()

class Asynchronizer(object):
    """
    An aeom.Asynchronizer executes object methods in a background process.  Its
    compute method accepts an object method, specified as object.method, a tuple
    of args and a dict of keyword args.  Subsequent calls to compute with the
    same parameters args will return None if the worker process is still running
    and otherwise will return the result.  The intended application is to allow
    a GUI to run a cpu-bound computation while still remaining responsive.  The
    GUI can poll the Asynchronizer on a timer, e.g. with window.after in
    Tkinter, until the result has been computed.  A pending computation can be
    cancelled by calling the cancel method; this kills the worker process.

    Instantiating an Asynchronizer creates a socket and launches a listener
    process listening on the socket for requests to compute things.  The
    listener process inherits an initialized copy of the Asynchronizer object,
    and uses its methods. Methods whose name begins with an underscore are meant
    to be called only from the listener process or, in the case of _task, from a
    worker process which is a child of the listener.  These methods should not
    be called from the process which instantiates the Asynchronizer.

    Caveats:

    * An Asynchronizer only works with objects and arguments that can be
      pickled, as it needs to send them through a socket.

    * This does not work in Python 2.7 because the pickle module refuses
      to pickle methods which are "not found as __main__.method".

    * If you use an Asynchronizer in a GUI app, create the object *before*
      loading the GUI module. Forking in a GUI process is frowned upon or,
      in the case of Apple, forbidden.
    """
    
    eol = b'\r\n'
    
    def __init__(self):
        self.socket = self.listener = None
        self.received = b''
        self.answers = {}
        family = socket.AF_INET if sys.platform == 'win32' else socket.AF_UNIX
        self.socket = socket.socket(family, socket.SOCK_STREAM)
        if family == socket.AF_UNIX:
            self.home = tempfile.mkdtemp(suffix='-Asynchronizer')
            self.socket_name = os.path.join(self.home, 'socket')
            self.socket.bind(self.socket_name)
        else:
            self.socket.bind(('127.0.0.1', 0))
            self.socket_name = self.socket.getsockname()
        self.listener = multiprocessing.Process(target=self._listen)
        self.listener.start()
        atexit.register(self.stop)
        
    def __del__(self):
        self.stop()

    def _listen(self):
        self._workers = {}
        self.socket.listen(5)
        while 1:
            # A side effect of calling this is that it cleans up zombies.
            children = multiprocessing.active_children()
            self._connection = self.socket.accept()[0]
            line = self.read_line(self._connection)
            if line == b'quit':
                for worker in children:
                    worker.terminate()
                self._send('BYE', connection)
                break
            self._run_command(line)
            self._connection.close()
        sys.exit()

    def _send(self, response):
        """
        Pickle a response and send it to the client.
        """
        try:
            pickled = pickle.dumps(response)
        except:
            pickled = pickle.dumps('Not a picklable result')
        self._connection.sendall(pickled + self.eol)

    def _run_command(self, line):
        if line.strip() == '':
            return
        words = line.split(None, 1) + [None]
        command, arg = words[:2]
        command = command.decode('utf-8')
        response = 'Unknown command: %s.'%command
        if command == 'save':
            question, answer = pickle.loads(arg)
            self.answers[question] = answer
        if command == 'cancel':
            worker = self._workers.pop(arg, None)
            answer = self.answers.pop(arg, None)
            if worker:
                worker.terminate()
            response = None
            # Prevent the dead worker from becoming a zombie.
            children = multiprocessing.active_children()
        elif command == 'compute':
            if arg in self.answers:
                response = self.answers[arg]
                if not isinstance(response, Pending):
                    # The answer will be cached by the main process.
                    self.answers.pop(arg)
                    self._workers.pop(arg)
                else:
                    response = pending
            else:
                process = multiprocessing.Process(target=self._task, args=(arg,))
                process.start()
                self.answers[arg] = pending
                self._workers[arg] = process
                response = pending
        self._send(response)

    def _task(self, question):
        """
        Workers run this to compute their answer.
        """
        method, args, kwargs = pickle.loads(question)
        try:
            answer = method(*args, **kwargs)
        except:
            answer = 'Failed'
        arg = pickle.dumps((question, answer))
        self.ask('save', arg)
        
    def read_line(self, receiver):
        """
        Read data from the receiver until eol is found and return everything before
        the eol as a byte sequence.  Save everything after the eol for the next
        call.
        """
        while 1:
            chunk = receiver.recv(4096)
            n = chunk.find(self.eol) if chunk else 0
            if n < 0:
                self.received += chunk
            else:
                line = self.received + chunk[:n]
                self.received = chunk[n+2:]
                break
        return line

    def stop(self):
        if self.listener and self.listener.is_alive():
            self.ask('quit')
            self.listener.terminate()
            self.listener = None
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.home:
            shutil.rmtree(self.home, True)
            self.home = None

    def ask(self, question, argument=None):
        """
        Send a question to the listener and return the pickled answer.  The question
        is a one-word string.  The optional argument is an arbitrary byte
        sequence with no encoding, typically a pickle.  Neither the question nor
        the argument should contain the eol marker (by default, carriage return
        followed by newline).
        
        This method is not intended for humans, due to its use of byte sequences.
        """
        if not self.socket:
            raise RuntimeError('No socket.')
        sock = socket.socket(self.socket.family, socket.SOCK_STREAM)
        try:
            sock.connect(self.socket_name)
        except socket.error:
            raise RuntimeError('Could not connect to listener.')
            sock.close()
            return
        data = question.encode('utf-8') + b' '
        assert data.find(self.eol) < 0 , 'The question contains an eol mark.'
        if argument:
            assert argument.find(self.eol) < 0 , 'The argument contains an eol mark.'
            data += argument
        sock.sendall(data + self.eol)
        answer = self.read_line(sock)
        sock.close()
        return answer

    def compute(self, method, args=tuple(), kwargs={}):
        """
        Evaluate the method using the given args and kwargs.  The method should be
        specified in dot notation, e.g. M.identify for the identify method of a
        snappy Manifold object M.  The answer will be computed asynchronously by
        a worker process and then cached.
        
        The return value will be a Pending object if the worker has not finished.
        """
        question = pickle.dumps((method, args, kwargs))
        if question in self.answers:
            return self.answers[question]
        answer = pickle.loads(self.ask('compute', question))
        if not isinstance(answer, Pending):
            self.answers[question] = answer
        return answer

    def cancel(self, method, args=tuple(), kwargs={}):
        """
        Cancel a pending computation - the worker process is terminated.
        """
        question = pickle.dumps((method, args, kwargs))
        if question not in self.answers:
            self.ask('cancel', question)

