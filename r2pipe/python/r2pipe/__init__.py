#/usr/bin/env python
# -*- coding: utf-8 -*-

"""r2pipe

This module provides an API to interact with the radare2
commandline interface from Python using a pipe.

The pipe can be connected to the parent process to run
Python scripts from the radare2 shell itself, or it can
spawn a new process, connect via HTTP to a remote r2 http
server, etc.

Some r2 commands display the information in JSON, that's
why r2pipe provides `-j` methods to directly parse it
and return a native Python object.

Example:
  $ python
  > import r2pipe
  > r = r2pipe.open("/bin/ls")
  > print(r.cmd("pd 10"))
  > print(r.cmdj("aoj")[0]['size'])
"""

import os
import re
import sys
import time
import json
import socket
from subprocess import Popen, PIPE

VERSION="0.6.6"

if sys.version_info >= (3,0):
	import urllib.request
	urlopen = urllib.request.urlopen
	import urllib.error
	URLError = urllib.error.URLError
else:
	import urllib2
	urlopen = urllib2.urlopen
	URLError = urllib2.URLError
if os.name=="nt":
	from ctypes import *
	import msvcrt
	GENERIC_READ = 0x80000000
	GENERIC_WRITE = 0x40000000
	OPEN_EXISTING = 0x3
	INVALID_HANDLE_VALUE = -1
	PIPE_READMODE_MESSAGE = 0x2
	ERROR_PIPE_BUSY = 231
	ERROR_MORE_DATA = 234
	BUFSIZE = 4096
	szPipename = "\\\\.\\pipe\\"
	chBuf = create_string_buffer(BUFSIZE)
	cbRead = c_ulong(0)
	cbWritten = c_ulong(0)

def version():
	"""Return string with the version of the r2pipe library
	"""
	return VERSION

class open:
	"""Class representing an r2pipe connection with a running radare2 instance
	"""
	def __init__(self, filename='', writeable=False, bininfo=True, debug=False,):
		"""Open a new r2 pipe
		The 'filename' can be one of the following:

		* absolute or relative path to file
		* http://<host>:<port>/cmd to connect to an r2 webserver
		* tcp://<host>:<port> to connect to an r2 tcp server
		* #!pipe when launching it from r2 via RLang.pipe

		Args:
			filename (str): path to filename or uri
			writeable (bool): if True opens the file in read-write
			bininfo (bool): if True loads the info from the binary
			debug (bool): if True opens in debugger (r2 -d)
		Returns:
			Returns an object with methods to interact with r2 via commands
		"""
		try:
			if os.name=="nt":
				mypipename=os.environ['r2pipe_path']
				while 1:
					hPipe = windll.kernel32.CreateFileA(szPipename+mypipename, GENERIC_READ |GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
					if (hPipe != INVALID_HANDLE_VALUE):
						break
					else:
						print ("Invalid Handle Value")
					if (windll.kernel32.GetLastError() != ERROR_PIPE_BUSY):
						print ("Could not open pipe")
						return
					elif ((windll.kernel32.WaitNamedPipeA(szPipename, 20000)) ==0):
						print ("Could not open pipe\n")
						return
				windll.kernel32.WriteFile(hPipe, "e scr.color=false\n",18, byref(cbWritten), None)
				windll.kernel32.ReadFile(hPipe, chBuf, BUFSIZE, byref(cbRead), None)
				self.pipe = [hPipe, hPipe]
				self._cmd = self._cmd_pipe
				self.url = "#!pipe"
				return
			else:
				self.pipe = [ int(os.environ['R2PIPE_IN']), int(os.environ['R2PIPE_OUT']) ]
				self._cmd = self._cmd_pipe
				self.url = "#!pipe"
				return
		except:
			pass
		if filename.startswith("#!pipe"):
			print("ERROR: Cannot use #!pipe without R2PIPE_{IN|OUT} env")
			return
		if filename.startswith("http"):
			self._cmd = self._cmd_http
			self.uri = filename + "/cmd"
		elif filename.startswith("tcp"):
			r = re.match(r'tcp://(\d+\.\d+.\d+.\d+):(\d+)/?', filename)
			if not r:
				raise Exception("String doesn't match tcp format")
			self._cmd = self._cmd_tcp
			self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.conn.connect((r.group(1), int(r.group(2))))
		else:
			self._cmd = self._cmd_process
			cmd = ["r2", "-q0", filename]
			if writeable:
				cmd = cmd[:1] + ["-w"] + cmd[1:]
			if debug:
				cmd = cmd[:1] + ["-d"] + cmd[1:]
			if not bininfo:
				cmd = cmd[:1] + ["-n"] + cmd[1:]
			self.process = Popen(cmd, shell=False, stdin=PIPE, stdout=PIPE)
			self.process.stdout.read(1) # Reads initial \x00

	def _cmd_process(self, cmd):
		if sys.version_info >= (3,0):
			self.process.stdin.write(bytes(cmd+'\n','utf-8'))
		else:
			self.process.stdin.write(cmd+'\n')
		self.process.stdin.flush()
		out = b''
		while True:
			foo = self.process.stdout.read(1)
			if foo == b'\x00':
				break
			if len(foo)<1:
				return None
			out += foo
		return out.decode('utf-8')

	def _cmd_tcp(self, cmd):
		res = b''
		self.conn.sendall(str.encode(cmd, 'utf-8'))
		data = self.conn.recv(512)
		while data:
			res += data
			data = self.conn.recv(512)
		return res.decode('utf-8')

	def _cmd_pipe(self, cmd):
		out = ''
		if os.name=="nt":
			fSuccess = windll.kernel32.WriteFile(self.pipe[1],cmd,len(cmd), byref(cbWritten), None)
			fSuccess = windll.kernel32.ReadFile(self.pipe[1], chBuf, BUFSIZE,byref(cbRead), None)
			out = chBuf.value
		else:
			os.write (self.pipe[1], cmd)
			while True:
				res = os.read (self.pipe[0], 4096)
				# chop in last
				if (len(res)<1):
					break
				out += res
				if res[-1] == b'\x00':
					out = out[0:-1]
					break
		return out.decode('utf-8')

	def _cmd_http(self, cmd):
		try:
			response = urlopen('{uri}/{cmd}'.format(uri=self.uri, cmd=cmd))
			return response.read().decode('utf-8')
		except URLError:
			pass
		return None

	# r2 commands
	def cmd(self, cmd):
		"""Run an r2 command return string with result
		Args:
			cmd (str): r2 command
		Returns:
			Returns an string with the results of the command
		"""
		return self._cmd(cmd)

	def cmdj(self, cmd):
		"""Same as cmd() but evaluates JSONs and returns an object
		Args:
			cmd (str): r2 command
		Returns:
			Returns a Python object respresenting the parsed JSON
		"""
		try:
			data = json.loads(self.cmd(cmd).encode('utf-8', 'ignore'))
		except (ValueError, KeyError, TypeError) as e:
			sys.stderr.write ("r2pipe.cmdj.Error: %s\n"%(e))
			data = None
		return data

	def syscmd(self, cmd):
		"""Executes a program and returns the output (stdout only)
		Args:
			cmd (str): commandline shell command
		Returns:
			Returns a string with the output
		"""
		p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE)
		out, err = p.communicate()
		return out

	def syscmdj(self, cmd):
		"""Executes a program and returns an object representing the parsed JSON of the output
		Args:
			cmd (str): commandline shell command
		Returns:
			Returns an object constructed by parsing the JSON returned by the command
		"""
		try:
			data = json.loads(self.syscmd(cmd))
		except (ValueError, KeyError, TypeError) as e:
			sys.stderr.write ("r2pipe.syscmdj.Error %s\n"%(e))
			data = None
		return data

# Hello World
if __name__ == "__main__":
	print("[+] Spawning r2 tcp and http servers")
	system ("pkill r2")
	system ("r2 -qc.:9080 /bin/ls &")
	system ("r2 -qc=h /bin/ls &")
	time.sleep(1)
	# Test r2pipe with local process
	print("[+] Testing python r2pipe local")
	rlocal = open("/bin/ls")
	print(rlocal.cmd("pi 5"))
	#print rlocal.cmd("pn")
	info = rlocal.cmdj("ij")
	print ("Architecture: " + info['bin']['machine'])

	# Test r2pipe with remote tcp process (launch it with "r2 -qc.:9080 myfile")
	print("[+] Testing python r2pipe tcp://")
	rremote = open("tcp://127.0.0.1:9080")
	disas = rremote.cmd("pi 5")
	if not disas:
		print("Error with remote tcp conection")
	else:
		print(disas)

	# Test r2pipe with remote http process (launch it with "r2 -qc=H myfile")
	print("[+] Testing python r2pipe http://")
	rremote = open("http://127.0.0.1:9090")
	disas = rremote.cmd("pi 5")
	if not disas:
		print("Error with remote http conection")
	else:
		print(disas)
	system ("pkill -INT r2")
