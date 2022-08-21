import socket
import sys
import threading
import time

class TCPServer:
	def __init__(self, host = '127.0.0.1', port = 12000):
		self.host = host
		self.port = port
		self.tcp_socket = None
		self.active_conn = 0
		self.max_active_connections = 0

	def handle_client(self, client_socket, addr):
		if self.active_conn > self.max_active_connections:
			print('Max limit exceeded! Waiting for 5 sec...')
			time.sleep(5)
			self.active_conn = 0
			return
		else:
			self.active_conn += 1
			data = client_socket.recv(65536)
			if data:
				response, message = self.handle_request(data, addr)
				client_socket.send(response.encode('ascii'))
				if message:
					client_socket.send(message)
			client_socket.shutdown(socket.SHUT_RDWR)
			self.active_conn -= 1
			client_socket.close()

	def start(self):
		#creating a TCP socket using IPv4 addresses 
		self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			try: 
				self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) # only available in linux/ BSD; not in windows
			except AttributeError:
				pass
			#self.tcp_socket.setblocking(False)
			self.tcp_socket.bind((self.host, self.port))

			self.tcp_socket.listen(5)

			print(f'Listening at: {self.tcp_socket.getsockname()}')

			while True:
				try:
					conn, addr = self.tcp_socket.accept() #conn = clientSocket
					print(f'{addr} connected!')
					clientHandler = threading.Thread(target = self.handle_client, args = (conn, addr))
					clientHandler.start()
					print(f"Connection closed {addr}")
					#clientHandler.join()
					
				except KeyboardInterrupt:
				   	sys.exit()
				except Exception as e:
					print(f"Exception {e}")

		finally:
			pass
	
	def handle_request(self, data, addr):
		return data.decode('iso-8859-1')
