import socket
from http import HTTPStatus
from TCP_Server import TCPServer
import mimetypes
import os
import shutil
from uuid import uuid4
import re
import time

#http request class for parsing and processing incoming reqs
class HTTPRequest:
	def __init__(self, data, addr):
		self.method = None
		self.uri = None
		self.http_version = '1.1'
		self.req_body = None
		self.req_headers = {}
		self.req_line = None
		self.client_ip = addr[0]
		self.parse(data)
	
	def parse(self, data):
		try:
			lines = data.decode('iso-8859-1').split('\r\n\r\n', 1)
		except:
			print('Data cant be decoded')
			lines = str(data).split('\r\n\r\n', 1)
		
		head = lines[0].split('\r\n')
		self.req_line = head[0]
		if len(head) > 1:
			self.req_headers = dict(i.split(': ') for i in head[1:])
			# message-body signaled by inclusion of Content-Length or Transfer-Encoding header field in request headers.
			if 'Content-Length' in self.req_headers.keys() or 'Transfer-Encoding' in self.req_headers.keys():
				self.req_body = lines[1]
		
		self.parse_req(self.req_line)
	
	def parse_req(self, req_line):
		words = req_line.split(' ')
		if len(words) > 0:
			self.method = words[0]
		
			if len(words) > 1:
				abs_path = re.sub("^http://localhost:\d+", '', words[1])
				self.uri = abs_path #the uri being requested

				if len(words) > 2:
					self.http_version = words[2]