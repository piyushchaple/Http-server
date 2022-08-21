import socket
import os
import shutil
import datetime
import tzlocal
from uuid import uuid4
import re
import time
from http import HTTPStatus
from email.utils import formatdate
from TCP_Server import TCPServer
from HTTP_request import HTTPRequest
import mimetypes

mimetypes.add_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx', strict=True)

COOKIE_LOG = '/logs/CookieLog'
CONFIG = 'httpserver.config'

#Now teaching the HTTP protocol to use TCP server
class HTTPServer(TCPServer):
	def __init__(self):
		super().__init__()
		self.res_body_len = 0
		self.file_type = None
		self.headers = {
			'Date' : None,
			'Server' : 'httpserver',
			'Content-Length' : None,
			'Content-Type' : None
		}

		self.config = self.handle_config()
		self.documentRoot = self.handle_document_root()
		self.max_active_connections = self.handle_active_connections()
		self.status_codes = {}
		self.log_file_locations = {}
		self.handle_log_file_locations()
	
		for stat in HTTPStatus:
			name = stat.name
			desc = stat.description
			val = stat.value
			self.status_codes[val] = (name, desc)


	# returns byte length of a string
	def clen(self, s):
		return len(s.encode('iso-8859-1'))
	
	# returns content type of a filename/path/URL (charset yet to be handled)
	def ctype(self, s):
		return mimetypes.guess_type(s)[0]

	

	def handle_log_file_locations(self):
		if self.config.get('ErrorLog'):
			self.log_file_locations['errorlog'] = self.config['ErrorLog']
		else:
			self.log_file_locations['errorlog'] = 'logs/error.log'

		if self.config.get('AccessLog'):
			self.log_file_locations['accesslog'] = self.config['AccessLog']
		else:
			self.log_file_locations['accesslog'] = 'logs/access.log'


	def handle_active_connections(self):
		if self.config.get('MaxActiveConn'):
			n = self.config.get('MaxActiveConn')

			if n > 1:
				return n
		return 100 #default max value

	def handle_document_root(self):
		if self.config.get('DocumentRoot'):
			docRoot = self.config['DocumentRoot'].strip("/")
			if os.path.exists(docRoot):
				return docRoot
			else:
				print("DocumentRoot Error: OS Path does not exist")
		return ""

	def handle_cookies(self):
		headers = ""

		if self.config.get('CookieName'):
			for cookie in self.config['CookieName']:
				if cookie[-1] != ';':
					headers += f'Set-Cookie: {cookie}={str(uuid4()).replace("-", "")}\r\n'
				else:
					name = cookie.split(';')[0]
					headers += f'Set-Cookie: {name}={str(uuid4()).replace("-", "")};'
					headers += cookie[cookie.find(';') + 1 : ] + '\r\n'
		
		return headers
		
	def handle_request(self, data, addr):
		req = HTTPRequest(data, addr)
		version = req.http_version.split('/')[1]
		if version != '1.1':
			handler = self.http_505_handler
		else:
			try:
				handler = getattr(self, f'handle_{req.method}')
				if req.uri == None:
					handler = self.http_400_handler
	
			except AttributeError:
				handler = self.http_501_handler

		response, message = handler(req)

		return response, message

	def http_400_handler(self, req):
		response_line = self.response_line(status_code=400)

		res_body = f"<h1>400 {self.status_codes[400][1]}</h1>\r\n"

		# getting content length of HTTP response body
		self.res_body_len = self.clen(res_body)

		self.file_type = 'text/html'
		response_headers = self.response_headers(req)
		blank_line = '\r\n'
		self.error_log(req, response_line)

		return f'{response_line}{response_headers}{blank_line}', res_body.encode('ascii')

	def http_505_handler(self, req):
		response_line = self.response_line(status_code=505)

		res_body = "<h1>505 HTTP Version Not Supported</h1>"

		# getting content length of HTTP response body
		self.res_body_len = self.clen(res_body)

		self.file_type = 'text/html'
		response_headers = self.response_headers(req)
		blank_line = '\r\n'
		self.error_log(req, response_line)

		return f'{response_line}{response_headers}{blank_line}', res_body.encode('ascii')
	
	def http_501_handler(self, req):
		response_line = self.response_line(status_code=501)

		res_body = "<h1>501 Not Implemented</h1>"

		# getting content length of HTTP response body
		self.res_body_len = self.clen(res_body)

		self.file_type = 'text/html'
		response_headers = self.response_headers(req)
		blank_line = '\r\n'
		self.error_log(req, response_line)

		return f'{response_line}{response_headers}{blank_line}', res_body.encode('ascii')

	
	def get_last_modified_time(self, filename):
		filetime = os.path.getmtime(filename)
		s = time.ctime(filetime).split()
		filetime = f'{s[0]}, {s[2]} {s[1]} {s[4]} {s[3]} GMT'	
		return filetime

	def if_modified_since_handler(self, giventime, filetime):
		f1 = datetime.datetime.strptime(filetime, '%a, %d %b %Y %H:%M:%S GMT')
		g1 = datetime.datetime.strptime(giventime, '%a, %d %b %Y %H:%M:%S GMT')
		if f1 > g1:
			return True, filetime
		else:
			return False, giventime

	def if_unmodified_since_handler(self, giventime, filetime):
		f1 = datetime.datetime.strptime(filetime, '%a, %d %b %Y %H:%M:%S GMT')
		g1 = datetime.datetime.strptime(giventime, '%a, %d %b %Y %H:%M:%S GMT')
		if f1 < g1:
			return True, filetime
		else:
			return False, giventime
	
	def handle_GET(self, req):
		filename = req.uri.strip('/')
		filename = os.path.join(self.documentRoot, filename) if filename != '' else filename
		blank_line = '\r\n'

		if os.path.exists(filename):
			if os.access(filename, os.R_OK):
				response_line = self.response_line(200)
			
				with open(filename, 'rb') as f:
					res_body = f.read()

				# getting content type of filename
				self.file_type = self.ctype(filename)

			else:
				response_line = self.response_line(401)
				res_body = "<h1>401 Unauthorized</h1>"
				res_body = res_body.encode('ascii')
				self.file_type = 'text/html'
				self.error_log(req, response_line)
				self.res_body_len = len(res_body)
				response_headers = self.response_headers(req)
				self.access_log(req, response_line, self.res_body_len)
				return f'{response_line}{response_headers}{blank_line}', res_body
		
		else:
			response_line = self.response_line(404)
			res_body = "<h1>404 Not Found</h1>"
			res_body = res_body.encode('ascii')
			self.file_type = 'text/html'
			self.error_log(req, response_line)
			self.res_body_len = len(res_body)
			response_headers = self.response_headers(req)
			self.access_log(req, response_line, self.res_body_len)
			return f'{response_line}{response_headers}{blank_line}', res_body

		# getting content length of HTTP response body
		self.res_body_len = len(res_body)
		lmtime = self.get_last_modified_time(filename)
		response_headers = self.response_headers(req, {'Last-Modified': lmtime})

		# checking if-modified-since 
		if 'If-Modified-Since' in req.req_headers.keys():
			x, val = self.if_modified_since_handler(req.req_headers['If-Modified-Since'], lmtime)
			if not x:
				response_line = self.response_line(304)
				self.res_body_len = 0
				response_headers = self.response_headers(req)
				self.access_log(req, response_line, self.res_body_len)
				return f'{response_line}{response_headers}{blank_line}', None

		# checking if-modified-since 
		if 'If-Unmodified-Since' in req.req_headers.keys():
			x, val = self.if_unmodified_since_handler(req.req_headers['If-Unmodified-Since'], lmtime)
			if not x:
				response_line = self.response_line(412)
				self.res_body_len = 0
				response_headers = self.response_headers(req)
				self.access_log(req, response_line, self.res_body_len)
				return f'{response_line}{response_headers}{blank_line}', None

		self.access_log(req, response_line, self.res_body_len)
		return f'{response_line}{response_headers}{blank_line}', res_body


	# File uploading yet to be handled
	def handle_POST(self, req):
		filename = req.uri.strip('/')
		response_line = self.response_line(200)
		curr_datetime = datetime.datetime.now()
		res_body = "<h1>Form has been submitted</h1>"
		data = req.req_body
		
		
		if req.req_headers['Content-Type'] == 'application/x-www-form-urlencoded':
			file_dir = os.path.join(self.documentRoot, "post_data", "post_data_urlencoded.txt")
			f = open(file_dir, 'a')
			if data:
				res = dict(i.split('=') for i in data.split('&'))
				for key, value in res.items():
					if '+' in value:
						res[key] = value.replace('+', ' ')
				f.write(str(curr_datetime) + ' : ' + str(res))
			else:
				f.write(str(curr_datetime) + ' : ' + 'No data')
			f.write('\n')


		elif req.req_headers['Content-Type'].split(';')[0] == 'multipart/form-data':
			file_dir = os.path.join(self.documentRoot, "post_data", "post_data_multipart.txt")
			f = open(file_dir, 'a')
			res = []
			if data:
				# getting the boundary value from headers
				boundary = req.req_headers['Content-Type'].split(';')[1]
				boundary_val = '--' + boundary.split('=')[1]
				# splitting on boundary value
				data = data.lstrip(boundary_val).split(boundary_val)[:-1]
				for i in data:
					i = i.strip('\r\n')
					l = i.split('\r\n\r\n', 1)
					head = l[0].split('\r\n')
					headers = head[0].split('; ')
					contype = []
					if len(head) > 1:
						# if file has been uploaded
						data = None
						contype.append(head[1])
						# getting file name that is uploaded
						filename = headers[2].split('=')[1].strip('"')
						filename = os.path.join(self.documentRoot, filename) if filename != '' else filename
						if len(l) > 1:
							data = l[1]
							data = data.encode('iso-8859-1')
							# creating the uploaded file on the server 
							if not os.path.exists(filename):
								response_line = self.response_line(201)
								if filename:
									f2 = open(filename, 'wb')
									if data:
										f2.write(data)
							content = [data.decode('iso-8859-1')]

						result = headers + contype + content
						res.append(result)
					else:
						if len(l) > 1:
							content = [l[1]]
						result = headers + contype + content
						res.append(result)
				
				f.write(str(curr_datetime) + ' : ' + str(res))
			else:
				f.write(str(curr_datetime) + ' : ' + 'No data')
			f.write('\n')

		# getting content length of HTTP response body
		self.res_body_len = self.clen(res_body)
		
		self.access_log(req, response_line, self.res_body_len)
		self.file_type = 'text/html'
		response_headers = self.response_headers(req)
		blank_line = '\r\n'

		return f'{response_line}{response_headers}{blank_line}', res_body.encode('ascii')
	def handle_config(self):
		with open(CONFIG, 'r') as f:
			conf = f.readlines()

		config = {}

		if len(conf):
			conf = [conf[i].strip('\r\n ') for i in range(len(conf)) if conf[i][0] != '\n' and conf[i][0] != '#']
			for item in conf:
				if item.find('#') != -1:
					item = item[ : item.find('#')]
				items = item.split(' ')
				if len(items) > 1:
					config_name = items[0]
					config_val = items[1]
					if config_name == 'CookieName':
						if items[-1][-1] != ';' and len(items) > 2:
							print('Invalid Config: Cookie definition syntax error')
							break
						cookie_pref = ' '.join(items[2 : ])
						config_val += f';{cookie_pref}' 
						if config.get(config_name):
							config[config_name].append(config_val)
						else:
							config[config_name] = [config_val]
					elif config_name == 'DocumentRoot':
						if config.get(config_name):
							print("Multiple DocumentRoot values found, config value set to the first value configuration")
						else:
							if len(items) > 2:
								print("Invalid config: DocumentRoot definition syntax error")
								break
							config[config_name] = str(config_val)
					elif config_name == "Server":
						if config.get(config_name):
							print("Multiple Server name values found, config value set to the first value configuration")
						else:
							if len(items) > 2:
								print("Invalid config: ServerName definition syntax error")
								break
							self.headers['Server'] = str(config_val)
							config[config_name] = str(config_val)
					elif config_name == "MaxActiveConn":
						if config.get(config_name):
							print("Multiple Max Active connections values found, config value set to the first value configuration")
						else:
							if len(items) > 2:
								print("Invalid config: Max Active Connections definition syntax error")
								break
							config[config_name] = int(config_val)
					elif config_name == "AccessLog":
						if config.get(config_name):
							print("Multiple Access log specifications found, config value set to the first value configuration")
						else:
							if len(items) > 2:
								print("Invalid config: Access Log")
								break
							config[config_name] = str(config_val)
					elif config_name == "ErrorLog":
						if config.get(config_name):
							print("Multiple Error log specifications found, config value set to the first value configuration")
						else:
							if len(items) > 2:
								print("Invalid config: Error Log")
								break
							config[config_name] = str(config_val)
					else:
						print(f"Configuration {config_name} not implemented!")
			#print(config)
		
		return config
	def handle_PUT(self, req):
		filename = req.uri.strip('/')
		data = req.req_body
		data = data.encode('iso-8859-1')
		resource_type = req.req_headers.get('Content-Type') if req.req_headers.get('Content-Type') else 'text/plain'
		resource_extension = mimetypes.guess_extension(resource_type)
		uri_extension = '.' + filename.split('.')[-1]

		if uri_extension != resource_extension:
			response_line = self.response_line(415)
			self.error_log(req, response_line)
		else:
			# creating/ modifying the file on the server
			filename = os.path.join(self.documentRoot, filename) if filename != '' else filename
			if os.path.exists(filename):
				# checking write permissions for modifying file
				if os.access(filename, os.W_OK):
					response_line = self.response_line(200)
					f = open(filename, 'w+b')
					if data:
						f.write(data)
				else:
					response_line = self.response_line(401)
					self.error_log(req, response_line)
			else:
				# creating file on server
				response_line = self.response_line(201)
				f = open(filename, 'wb')
				if data:
					f.write(data)

		self.res_body_len = 0
		self.access_log(req, response_line, self.res_body_len)
		response_headers = self.response_headers(req, {'Content-Location': filename})
		blank_line = '\r\n'

		return f'{response_line}{response_headers}{blank_line}', None

	def handle_HEAD(self, req):
		# contains meta info about the reponse
		# identical to GET except doesnt return the response body 
		filename = req.uri.strip('/')
		filename = os.path.join(self.documentRoot, filename) if filename != '' else filename
		blank_line = '\r\n'

		if os.path.exists(filename):
			if os.access(filename, os.R_OK):
				response_line = self.response_line(200)
				with open(filename, 'rb') as f:
					res_body = f.read()

				# In HEAD, content type is of the file that would have been sent had the request been a GET
				self.file_type = self.ctype(filename)
			else:
				response_line = self.response_line(401)
				res_body = "<h1>401 Unauthorized</h1>"
				res_body = res_body.encode('ascii')
				self.file_type = 'text/html'
				self.error_log(req, response_line)
				self.res_body_len = len(res_body)
				self.access_log(req, response_line, self.res_body_len)
				response_headers = self.response_headers(req)
				return f'{response_line}{response_headers}{blank_line}', None

		else:
			response_line = self.response_line(404)
			res_body = "<h1>404 Not Found</h1>"
			res_body = res_body.encode('ascii')
			self.file_type = 'text/html'
			self.error_log(req, response_line)
			self.res_body_len = len(res_body)
			self.access_log(req, response_line, self.res_body_len)
			response_headers = self.response_headers(req)
			return f'{response_line}{response_headers}{blank_line}', None

		# In HEAD, content length is the size of the entity-body that would have been sent had the request been a GET.
		self.res_body_len = len(res_body)
		lmtime = self.get_last_modified_time(filename)
		response_headers = self.response_headers(req, {'Last-Modified': lmtime})

		# checking if-modified-since 
		if 'If-Modified-Since' in req.req_headers.keys():
			x, val = self.if_modified_since_handler(req.req_headers['If-Modified-Since'], lmtime)
			if not x:
				response_line = self.response_line(304)
				self.res_body_len = 0
				response_headers = self.response_headers(req)
		
		# checking if-unmodified-since 
		if 'If-Unmodified-Since' in req.req_headers.keys():
			x, val = self.if_unmodified_since_handler(req.req_headers['If-Unmodified-Since'], lmtime)
			if not x:
				response_line = self.response_line(412)
				self.res_body_len = 0
				response_headers = self.response_headers(req)
				self.access_log(req, response_line, self.res_body_len)
				return f'{response_line}{response_headers}{blank_line}', None

		self.access_log(req, response_line, self.res_body_len)
		return f'{response_line}{response_headers}{blank_line}', None

	def handle_DELETE(self, req):
		filename = req.uri.strip('/')
		filename = os.path.join(self.documentRoot, filename) if filename != '' else filename
		if os.path.exists(filename):
			if os.path.isfile(filename):
				os.remove(filename)
			elif os.path.isdir:
				shutil.rmtree(filename)
				
			response_line = self.response_line(200)
			res_body = f"<h1>File Deleted.</h1>"
			
		else:
			response_line = self.response_line(404)
			res_body = "<h1>404 Not Found</h1>"
			self.error_log(req, response_line)
		
		# getting content length of HTTP response body
		self.res_body_len = self.clen(res_body)
		
		self.file_type = 'text/html'
		self.access_log(req, response_line, self.res_body_len)
		response_headers = self.response_headers(req)
		blank_line = '\r\n'

		return f'{response_line}{response_headers}{blank_line}', res_body.encode('ascii')

	def response_line(self, status_code):
		status = self.status_codes[status_code][0]
		return f'HTTP/1.1 {status_code} {status}\r\n'
	
	def response_headers(self, req, extra_headers = {}):
		# the date and time at which message was originated (location of this line of code is uncertain)
		self.headers['Date'] = formatdate(timeval=None, localtime=False, usegmt=True) 

		self.headers['Content-Length'] = self.res_body_len
		#print(self.res_body_len)#519530
		self.headers['Content-Type'] = self.file_type

		res_headers = self.headers.copy()

		if extra_headers:
			res_headers.update(extra_headers)
		
		headers = ""

		if req.req_headers.get('Cookie') == None:
			headers += self.handle_cookies()

		for header in res_headers:
			headers += f'{header}: {res_headers[header]}\r\n'

		return headers	

	# logging all requests in access logs
	def access_log(self, req, response_line, size):
		timezone = tzlocal.get_localzone()
		curr_datetime = datetime.datetime.now(timezone).strftime("%d/%b/%Y:%H:%M:%S %z")
		status_code = response_line.split(' ')[1]
		f = open(self.log_file_locations['accesslog'], 'a+')
		f.write(f"{req.client_ip} - - [{curr_datetime}] \"{req.req_line}\" {status_code} {size}\n")
		f.close()

	# logging errors in error logs
	def error_log(self, req, response_line):
		timezone = tzlocal.get_localzone()
		curr_datetime = datetime.datetime.now(timezone).strftime("%d/%b/%Y:%H:%M:%S %z")
		status_code = response_line.split(' ')[1]
		error_msg = response_line.split(' ')[2].rstrip('\r\n')
		f = open(self.log_file_locations['errorlog'], 'a+')
		# defined two levels of logging - client and server
		if int(status_code) >= 400 and int(status_code) < 500:
			level = 'client'
			f.write(f"[{curr_datetime}] \"{req.req_line}\" [{level} error] [client {req.client_ip}] {status_code} {error_msg}\n")
		else:
			level = 'server'
			f.write(f"[{curr_datetime}] \"{req.req_line}\" [{level} error] [client {req.client_ip}] {status_code} {error_msg}\n")

		f.close()

if __name__ == '__main__':
	server = HTTPServer()
	server.start()	

