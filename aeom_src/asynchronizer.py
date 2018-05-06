#   Copyright (C) 2018-present Marc Culler, Nathan Dunfield and others.
#
#   This program is distributed under the terms of the
#   GNU General Public License, version 2 or later, as published by
#   the Free Software Foundation.  See the file gpl-2.0.txt for details.
#   The URL for this program is
#     https://bitbucket.org/t3m/aeom
#   A copy of the license file may be found at:
#     http://www.gnu.org/licenses/old-licenses/gpl-2.0.html

from __future__ import print_function
import sys, os, socket, tempfile, shutil, multiprocessing, atexit, hashlib, signal

if sys.version_info.major > 2:
    from pickle import loads, dumps
else:
    from dill import loads, dumps

from .pending import Pending

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

    * Asynchronizer.compute requires that the method, arguments and result
      can be pickled.

    * This does not work in Python 2.7 because the pickle module refuses
      to pickle methods which are "not found as __main__.method".

    * To make the listener process as small as possible, create the
      Asynchronizer object before importing other modules.  If you use an
      Asynchronizer in a GUI app, it may be *required* to do this; forking a GUI
      process is frowned upon or, at least in the case of Apple, forbidden.

    * On Windows, which does not support fork, there is a substantial amount of
      overhead involved in launching each worker process.

    """

    eol = b'\r\n'

    def __init__(self):
        self.socket = self.listener = self.home = None
        self.received = b''
        self.workers = {}
        self.answers = {}
        #self.queue = multiprocessing.Queue()
        family = socket.AF_INET if sys.platform == 'win32' else socket.AF_UNIX
        self.socket = socket.socket(family, socket.SOCK_STREAM)
        if family != socket.AF_INET:
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
        # Just in case, this is a second chance to kill all subprocesses.
        self.stop()

    def _listen(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            signal.signal(signal.SIGBREAK, signal.SIG_IGN)
        except AttributeError:
            pass
        self.server = multiprocessing.Process(target=self.server_task)
        self.socket.listen(5)
        while 1:
            # A documented side effect of this is to clean up zombie processes.
            children = multiprocessing.active_children()
            self._connection = self.socket.accept()[0]
            line = self.read_line(self._connection)
            stop = self._run_command(line)
            self._connection.close()
            if stop:
                break
        children = multiprocessing.active_children()

    def _run_command(self, line):
        result = False
        #print('listener received line:', line)
        if line.strip() == '':
            return result
        words = line.split(b' ', 1) + [None]
        command, arg = words[:2]
        command = command.decode('utf-8')
        if command == 'worker': # arg = b'%s %s'%(qid, pickled_question)
            qid, arg = arg.split(b' ', 1)
            method, args, kwargs = loads(arg)
            process = multiprocessing.Process(target=self._worker_task,
                                              args=(qid, method)+args,
                                              kwargs=kwargs)
            process.start()
            self.workers[qid] = process
            self.answers[qid] = response = dumps(Pending(pid=process.pid))
        elif command == 'server':
            if self.server.pid is None:
                self.server.start()
            elif not self.server.is_alive():
                self.server = multiprocessing.Process(target=self.server_task)
                self.server.start()
                multiprocessing.active_children()
            qid, arg = arg.split(b' ', 1)
            method, args, kwargs = loads(arg)
            #self.queue.put((qid, method, args, kwargs))
            self.answers[qid] = response = dumps(Pending(pid=self.server.pid))
        elif command == 'save': # arg = b'%s %s'%(qid, pickled_answer)
            qid, answer = arg.split(b' ', 1)
            self.answers[qid] = answer
            self.workers.pop(qid, None)
            multiprocessing.active_children()
            response = dumps('OK')
        elif command == 'fetch': # arg = b'%s'%qid
            # If we don't recognize the qid, return it as a pickle.
            response = self.answers.pop(arg, dumps(arg))
        elif command == 'stop':
            for worker in multiprocessing.active_children():
                worker.terminate()
            response = dumps('OK')
            result = True
        else:
            response = dumps('Unknown command')
        self._connection.sendall(response + self.eol)
        return result
    
    def _worker_task(self, *args, **kwargs):
        """
        Workers run this to compute their answer.
        """
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            signal.signal(signal.SIGBREAK, signal.SIG_IGN)
        except AttributeError:
            pass
        qid, method = args[:2]
        args = args[2:]
        #print(method)
        try:
            answer = method(*args, **kwargs)
        except Exception as e:
            answer = 'Failed: %s'%e
        arg = b'%s %s'%(qid, dumps(answer))
        #print('worker sending arg:', arg)
        self.ask('save', arg)
#        sys.exit()

    def server_task(self):
        """
        The server runs this.  It waits for a request to be added to the
        queue and then computes the answer and sends it to the listener.
        """
        # We probably want the server to handle SIGINTs, as an abort signal.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            signal.signal(signal.SIGBREAK, signal.SIG_IGN)
        except AttributeError:
            pass
        #print('server started')
        while True:
            # Block until a question appears,
            #qid, method, args, kwargs = self.queue.get()
            #print('server:', method, args, kwargs)
            # then compute the answer.
            try:
                answer = method(*args, **kwargs)
            except Exception as e:
                answer = 'Failed: %s'%e
            arg = b'%s %s'%(qid, dumps(answer))
            self.ask('save', arg)
        sys.exit()

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
        #print('Stopping')
        if self.listener.is_alive():
            response = self.ask('stop')
            self.listener.join(2)
            if self.listener.is_alive():
                self.listener.terminate()
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.home:
            shutil.rmtree(self.home, True)
            self.home = None

    def ask(self, request, argument=None):
        """
        Send a request to the listener and return a pickled response.  The request
        is a one-word string.  The optional argument is an arbitrary byte
        sequence with no encoding, typically a pickle.  Neither the request nor
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
        data = request.encode('utf-8') + b' '
        assert data.find(self.eol) < 0 , 'The request contains an eol mark.'
        if argument:
            assert argument.find(self.eol) < 0 , 'The argument contains an eol mark:\n%s'%argument
            data += argument
        sock.sendall(data + self.eol)
        response = self.read_line(sock)
        sock.close()
        return response

    def get_qid(self, method, args, kwargs):
        """
        Generate a python-hashable unique identifier for (method, args, kwargs).
        Note: the code in _run_command assumes that the qid is a byte sequence
        that does not contain any spaces, which can happen with md5.digest.
        """
        args = dumps((method, args, kwargs))
        return hashlib.md5(args).hexdigest().encode('ascii'), args
        # This might be faster, but would get confused if distinct args had the same repr.
        # return hashlib.md5(('%s %s %s'%(method, args, kwargs)).encode('utf-8')).digest()

    def compute(self, method, *args, **kwargs):
        """
        Asynchronously evaluate the method using the args and kwargs.  The method
        should be specified in dot notation, e.g. M.identify for the identify
        method of a snappy Manifold object M.

        The return value will be a Pending object if the worker has not finished.
        """
        qid, args = self.get_qid(method, args, kwargs)
        try:
            return self.answers[qid]
        except KeyError:
            pass
        answer = loads(self.ask('fetch', qid))
        if isinstance(answer, bytes) and answer == qid:
            answer = loads(self.ask('worker', qid + b' ' + args))
        if not isinstance(answer, Pending):
            self.answers[qid] = answer
        return answer

    def queue_compute(self, method, *args, **kwargs):
        """
        Queue a request for the server to evaluate the method using the args
        and kwargs.  The method should be specified in dot notation,
        e.g. M.identify for the identify method of a snappy Manifold object
        M.

        The return value will be a Pending object until the server has
        finished the computation.

        When the startup overhead for a worker is large, e.g. when the method
        is defined in a complex extension module *and* this is running on
        Windows then a server may be faster than a worker since the server
        only starts once.
        """
        qid, args = self.get_qid(method, args, kwargs)
        try:
            return self.answers[qid]
        except KeyError:
            pass
        answer = loads(self.ask('fetch', qid))
        if isinstance(answer, bytes) and answer == qid:
            answer = loads(self.ask('server', qid + b' ' + args))
        if not isinstance(answer, Pending):
            self.answers[qid] = answer
        return answer

    def cancel(self, method, *args, **kwargs):
        """
        Cancel a pending computation - This terminates the process which
        is working on the question.
        """
        qid, args = self.get_qid(method, args, kwargs)
        answer = self.answers.get(qid, None)
        if isinstance(answer, Pending):
            self.answers.pop(qid)
            if answer.pid == self.server.pid:
                process = self.server
                self.server = multiprocessing.Process(target=self.server_task)
            else:
                process = self.workers.pop(qid, None)
            if process and process.is_alive():
                process.terminate()
            # Prevent the dead process from becoming a zombie.
            while process.is_alive():
                pass
            children = multiprocessing.active_children()
