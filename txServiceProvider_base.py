#!/bin/env python3
"""
Telex Service Provider Base
This handles the connection to a client in two ways:
- The i-telex-communication protocol
- Runs the actual program of the service (must be a derived class from this base)
"""

import sys
import time
from threading import Thread
import socket
from txsReleaseInfo import ReleaseInfo

import logging
l = logging.getLogger("txs." + __name__)

import txCode



# i-Telex allowed package types for Baudot texting mode
# (everything else triggers ASCII texting mode)
from itertools import chain
allowed_types = lambda: chain(range(0x00, 0x09+1), range(0x10, 0x1f+1))

#######

# Decoding and encoding of extension numbers (see i-Telex specification, r874)
#
#            encoded         decoded
# (raw network data)    (as dialled)
#
#                  0            none
#                  1              01
#                  2              02
#                ...             ...
#                 99              99
#                100              00
#                101               1
#                102               2
#                ...
#                109               9
#                110               0
#               >110         invalid

def decode_ext_from_direct_dial(ext:int) -> str:
    """
    Decode integer extension from direct dial packet and return as str.
    """
    ext = int(ext)
    if ext == 0:
        return None
    elif 1 <= ext <= 100:
        # Two-digit extension (leading zero if applicable)
        return "{:02d}".format(ext%100)
    elif 101 <= ext <= 110:
        # single-digit extension
        return str(ext%10)
    else:
        # invalid!
        l.warning("Invalid direct dial extension: {} (falling back to 0)".format(ext))
        return None

def encode_ext_for_direct_dial(ext:str) -> int:
    """
    Encode str extension to integer extension for direct dial packet and return
    it.
    """
    if not ext:
        # no extension
        return 0
    try:
        ext_int = int(ext)
    except (ValueError, TypeError):
        l.warning("Invalid direct dial extension: {!r} (falling back to none)".format(ext))
        return 0
    if len(ext) == 1:
        return 110 if not ext_int else ext_int + 100
    elif len(ext) == 2:
        return 100 if not ext_int else ext_int
    else:
        l.warning("Invalid direct dial extension: {!r} (falling back to none)".format(ext))
        return 0

def display_hex(data:bytes) -> str:
	"""
	Convert a byte string into a string of hex values for diplay.
	"""
	return " ".join(hex(i) for i in data)


# Types of reject packets (see txDevMCP):
#
# - abs   line disabled
# - occ   line occupied
# - der   derailed: line connected, but called teleprinter not starting
#         up
# - na    called extension not allowed
def send_reject(self, s, msg = "abs"):
	'''Send reject packet (4)'''
	send = bytearray([4, len(msg)])   # Reject
	send.extend([ord(i) for i in msg])
	l.debug('Sending i-Telex packet: Reject ({})'.format(display_hex(send)))
	l.info('Reject, reason {!r}'.format(msg))
	s.sendall(send)

class TelexConnClosed(Exception):
	pass

class TelexServiceProvider_base():
	WRU = '12345 txss d'
	ignoreWRU = False
	_BuZi = '<'

	def __init__(self):
		self._rx_buffer = []
		self._tx_buffer = []
		self._acknowledge_counter = 0
		self._send_acknowledge_idle = False

###########################################################################################

	def send(self, s: str):
		for c in s:
			self._tx_buffer.append(c)

	def clearInputBuffer(self):
		self._rx_buffer.clear()
		return

	def getInputLen(self):
		return len(self._rx_buffer)
	def getOutputLen(self):
		return len(self._tx_buffer)
	def getLastBuZiMode(self):
		return self._BuZi

	def requestWru(self):
		self.send('@')
#		owru = self.recvUntil(['\n'])[0]+self.recvUntil(['\n'])[0]
		
		lasttime = time.monotonic()
		lastLen  = 0
		gotInput = True
		# is_running() is needed, because connection could be closed and _tx_buffer has still contents
		while self.is_running() and self.getOutputLen() > 0 and gotInput:
#			time.sleep(len(self._tx_buffer)*0.15) # needs to much time
			
			time.sleep(0.15)
			if self.getOutputLen() > 0:
				continue
			
			newLen = self.getInputLen()
			if newLen > lastLen:
				lastLen = newLen
				lasttime = time.monotonic()
			elif newLen == lastLen:
				now = time.monotonic()
				if (now - lasttime > 1):
					gotInput = False
			
			
		time.sleep(3)
		owru = ''
		while self.getInputLen() > 0:
			c = self.recvChar()
			if c in ['<','>','@','\r','\n']:
				continue
			owru += c
			
#			# in case rx buffer is already empty, wait additional two char length
#			if (self.getInputLen() == 0):
#				time.sleep(0.3)
		
		return owru.strip()

	def recvChar(self, returnWRU = False) -> str:
		c = ''
		# wait until new char arrives and connection is running
		while len(self._rx_buffer) == 0 and self.is_running():
			time.sleep(0.15) # 1 char is 1x start bit, 5x data, 1.5 stop = 0.15s
		# if we got chars, try to get one
		if len(self._rx_buffer) > 0:
			try:
				c = self._rx_buffer.pop(0)
			except Exception:
				# catch any possible exception (can be there one?)
				pass
		# if _rx_buffer still empty, the connection must be closed. Either by peer or by us.
		# in both cases, we want to get to an end. So we raise an exception which only is catched
		# at the point where the subroutine for this server is called.
		# So no "is_running" is needed at every reading while loop anymore.
		else:
			raise TelexConnClosed()
		if c in ['<','>']:
			self._BuZi = c
#		print('>'+c+'<')
		if (c == '@'):
			if not self.ignoreWRU:
				self.send('\r\n'+self.WRU)
			if not returnWRU:
				return ''
		return c.lower()

	def recvUntil(self, stop) -> [str, str]:
		ast = ''
		c = ''
		while not c in stop:
			c = self.recvChar()
			if c == '<' or c == '>':
				continue
			ast += c
#		print('>'+ast+'<')
		return ast, c

	def recvLine(self) -> str:
		s,e = self.recvUntil(['\n'])
		return s

#	DONT USE IF YOU WANT SUPPORT MORE MODERN TELEX MACHINES!
	def recvCorrLine_old(self) -> str:
		l.warning('recvCorrLine is not usable on more modern telex machines, because they always send \\r\\n!')
		s,e = self.recvUntil(['\n'])
		return s[s.rfind('\r')+1:]
		
	def recvCorrLine(self, cancelStr = 'xxx', onlyAtEnd = True) -> str:
		s,e = self.recvUntil(['\n'])
		s = s.strip()
		lenCS = len(cancelStr)
		if (s[-lenCS:] == cancelStr):
			return ''
		p = s.rfind(cancelStr)
		if (not onlyAtEnd and (p >= 0)):
			return s[p+lenCS:]
		return s

	def recvFile(self, stop = '(eof)') -> str:
		ast = ''
		tmp = ''
		
		while tmp != stop:
			c = self.recvChar()
			if c == '<' or c == '>':
				continue
			tmp += c
			if not (stop.startswith(tmp)):
				ast += tmp
				tmp = ''
		return ast

# For developer:
# Try to use getInput…, because it sends the last state of BuZi-state automatically.
# So the teletype printer and keyboard will be in the same state.
	def getInput(self, prompt = '', end = ': '):
		inp = ''
		while inp == '':
			if len(prompt) > 0:
				self.send(prompt+end)
			self.send(self._BuZi)
			inp = self.recvCorrLine().strip()
			self.send('\r')
		return inp

	def getInputOption(self, validOptions, prompt = '', end = ': '):
		opt = ''
		while (opt == '' or not opt in validOptions):
			if len(prompt) > 0:
				self.send(prompt+end)
			self.send(self._BuZi)
			opt = self.recvCorrLine().strip()
			
			opt = self._validOptionStartsWith(opt, validOptions)
			
			self.send('\r')
		return opt
	def _validOptionStartsWith(self, opt, validOptions):
		ret = ''
		for vo in validOptions:
			if opt == vo:
				return vo
		for vo in validOptions:
			if vo.startswith(opt):
				if len(ret) > 0:
					return ''
				else:
					ret = vo
		return ret

###########################################################################################



	def is_running(self):
		return not self._stop.is_set() and self._t.is_alive()

	def handle_client(self, s:socket.socket, addr, sema, stop):
		# start the i-telex-connection thread
		self._stop = stop
		self._t = Thread(target=self.handle_client_conn, name='txsConn', args=(s,addr,sema))
		self._t.start()
		
		try:
			# now do what to do
			self.doHandleClient()
		except TelexConnClosed:
			l.info('Conn closed while reading.')
		except:
			# catch any possible exception so we can come to an end cleanly.
#			raise
			pass
		finally:
			# wait to flush the _tx_buffer (if connection still there)
			while self.is_running() and self._tx_buffer:
				time.sleep(len(self._tx_buffer)*0.15)
			self.send_end(s)
	
	# just for deriving purpose
	def doHandleClient(self):
		self.send('\r\nservice provider base class. not meant to be called.\r\n')

	# do the i-telex-connection thing
	def handle_client_conn(self, s:socket.socket, addr, sema):
		"""Handles a client or server connection."""

		# print("process_connection")
		
		
		time_2Hz = time.monotonic()
		time_20Hz = time.monotonic()
		time_200Hz = time.monotonic()
		
		try:
			#s.sendall(b"Welcome! Send data and it will be echoed back.\n")
			
			is_ascii = None
			
			bmc = txCode.BaudotMurrayCode(False, False, True)
			sent_counter = 0
			self._received_counter = 0
			timeout_counter = -1
			time_next_send = None
			error = False

			s.settimeout(0.2)

			# Store remote protocol version to control negotiation
			self._remote_protocol_ver = None

			self._acknowledge_counter = self._last_acknowledge_counter = 0 #-24 # fixed length of welcome banner, see txDevMCP

			self.send_ack(s, 0) # -24 # fixed length of welcome banner, see txDevMCP

			while not self._stop.is_set():
			
				# time-things
				time_act = int(time.monotonic() * 1000)   #time in ms
				if (time_act - time_2Hz) >= 500:
					time_2Hz = time_act
					
					# process idle2Hz

					# Send Acknowledge if fully connected (only set flag because we're out
					# of context)
					self._send_acknowledge_idle = True



			
			
				try:
					data = s.recv(1)

					# piTelex terminates; close connection
					#if not self._run:
					#	break

					# lost connection
					if not data:
						l.warning("Remote has closed connection")
						break

					# Telnet control sequence
					elif data[0] == 255:
						d = s.recv(2)   # skip next 2 bytes from telnet command

					# i-Telex packet
					elif data[0] in allowed_types():
						packet_error = False

						d = s.recv(1)
						data += d
						packet_len = d[0]
						if packet_len:
							data += s.recv(packet_len)

						# Heartbeat
						if data[0] == 0 and packet_len == 0:
							l.debug('Received i-Telex packet: Heartbeat ({})'.format(display_hex(data)))

						# Direct Dial
						elif data[0] == 1 and packet_len == 1:
							l.debug('Received i-Telex packet: Direct dial ({})'.format(display_hex(data)))

							# Disable emitting "direct dial" command, since it's
							# currently not acted upon anywhere.
							#with self._rx_lock:
							#	self._rx_buffer.append('\x1bD'+str(data[2]))

							# Instead, only accept extension 0 (i-Telex default)
							# and None, and reject all others.
							ext = decode_ext_from_direct_dial(data[2])
							l.info('Direct Dial, extension {}'.format(ext))
							if not ext in ('0', None):
								self.send_reject(s, 'na')
								error = True
								break

						# Baudot Data
						elif data[0] == 2 and packet_len >= 1 and packet_len <= 50:
							l.debug('Received i-Telex packet: Baudot data ({})'.format(display_hex(data)))
							aa = bmc.decodeBM2A(data[2:])
#							with self._rx_lock:
							for a in aa:
#								if a == '@':
#									a = '#'
								self._rx_buffer.append(a)
								
							self._received_counter += len(data[2:])
							# Send Acknowledge if printer is running and we've got
							# at least 16 characters left to print
#							if self._print_buf_len >= 16:
#								self.send_ack(s, self._acknowledge_counter)
							self.send_ack(s, self._received_counter)

						# End
						elif data[0] == 3 and packet_len == 0:
							l.debug('Received i-Telex packet: End ({})'.format(display_hex(data)))
							l.info('End by remote')
							break

						# Reject
						elif data[0] == 4 and packet_len <= 20:
							l.debug('Received i-Telex packet: Reject ({})'.format(display_hex(data)))
							aa = data[2:].decode('ASCII', errors='ignore')
							# i-Telex may pad with \x00 (e.g. "nc\x00"); remove padding
							aa = aa.rstrip('\x00')
							l.info('i-Telex connection rejected, reason {!r}'.format(aa))
							break

						# Acknowledge
						elif data[0] == 6 and packet_len == 1:
							l.debug('Received i-Telex packet: Acknowledge ({})'.format(display_hex(data)))
							# TODO: Fix calculation and prevent overflows, e.g. if
							# the first ACK is sent with a low positive value. This
							# might be done by saving the first ACK's absolute
							# counter value and only doing difference calculations
							# afterwards.
							unprinted = (sent_counter - int(data[2])) & 0xFF
							#if unprinted < 0:
							#	unprinted += 256
							l.debug(str(data[2])+'/'+str(sent_counter)+'='+str(unprinted) + " (printed/sent=unprinted)")
							if unprinted < 7:   # about 1 sec
								time_next_send = None
							else:
								time_next_send = time.monotonic() + (unprinted-6)*0.15
							# Send Acknowledge if printer is running and remote end
							# has printed all sent characters
							# ! Better not, this will create an Ack flood !
							# if self._connected >= ST.CON_FULL and unprinted == 0:
							#	 self.send_ack(s, self._acknowledge_counter)


						# Version
						elif data[0] == 7 and packet_len >= 1 and packet_len <= 20:
							aa = ''
							if packet_len > 1:
								aa = data[3:].decode('ASCII', errors='ignore')
								aa = aa.rstrip('\x00')
							l.info(f"Received i-Telex packet: Version {data[2]} '{aa}' ({display_hex(data)})")
							if self._remote_protocol_ver is None:
								if data[2] != 1:
									# This is the first time an unsupported version was offered
									l.warning("Unsupported version offered by remote ({}), requesting v1".format(display_hex(data[2:])))
									self.send_version(s)
								else:
									# Only send version packet in response to valid
									# version when we're server, because as client,
									# we sent a version packet directly after
									# connecting.
									self.send_version(s)
								# Store offered version
								self._remote_protocol_ver = data[2]
							else:
								if data[2] != 1:
									# The remote station insists on incompatible
									# version. Send the not-officially-defined
									# error code "ver".
									l.error("Unsupported version insisted on by remote ({})".format(display_hex(data[2:])))
									self.send_reject(s, 'ver')
									error = True
									break
								else:
									if data[2] != self._remote_protocol_ver:
										l.info("Negotiated protocol version {}, initial request was {}".format(data[2], self._remote_protocol_ver))
										self._remote_protocol_ver = data[2]
									else:
										# Ignore multiple good version packets
										l.info("Redundant Version packet")

						# Self test
						elif data[0] == 8 and packet_len >= 2:
							l.debug('Received i-Telex packet: Self test ({})'.format(display_hex(data)))

						# Remote config
						elif data[0] == 9 and packet_len >= 3:
							l.info('Received i-Telex packet: Remote config ({})'.format(display_hex(data)))

						# Wrong packet - will resync at next socket.timeout
						else:
							l.warning('Received invalid i-Telex Packet: {}'.format(display_hex(data)))
							packet_error = True

						if not packet_error:
							if is_ascii is None:
								l.info('Detected i-Telex connection')
								is_ascii = False
							elif is_ascii:
								l.warning('Detected i-Telex connection, but ASCII was expected')
								is_ascii = False

						# Also send Acknowledge packet if triggered by idle function
						if self._send_acknowledge_idle:
							self._send_acknowledge_idle = False
#							self.send_ack(s, self._acknowledge_counter)
							self.send_ack(s, self._received_counter)

					# ASCII character(s)
					else:
						l.debug('Received non-i-Telex data: {} ({})'.format(repr(data), display_hex(data)))

						if self._block_ascii:
							l.warning("Incoming ASCII connection blocked")
							break

						if is_ascii is None:
							l.info('Detected ASCII connection')
							is_ascii = True
						elif not is_ascii:
							l.warning('Detected ASCII connection, but i-Telex was expected')
							is_ascii = True
						
						data = data.decode('ASCII', errors='ignore').upper()
						data = txCode.BaudotMurrayCode.translate(data)
						#with self._rx_lock:
						for a in data:
#							if a == '@':
#								a = '#'
							self._rx_buffer.append(a)
							self._received_counter += 1

				except socket.timeout:
					#l.debug('.')
					if is_ascii is not None:   # either ASCII or baudot connection detected
						timeout_counter += 1

						if is_ascii:
							if self._tx_buffer:
								sent = self.send_data_ascii(s)
								sent_counter += sent

						else:   # baudot
							if (timeout_counter % 5) == 0:   # every 1 sec
								# Send Acknowledge if printer is running
#								self.send_ack(s, self._acknowledge_counter)
								self.send_ack(s, self._received_counter)

							if self._tx_buffer:
								if time_next_send and time.monotonic() < time_next_send:
									l.debug('Sending paused for {:.3f} s'.format(time_next_send-time.monotonic()))
									pass
								else:
									sent = self.send_data_baudot(s, bmc)
									sent_counter += sent
									if sent > 7:
										time_next_send = time.monotonic() + (sent-6)*0.15

							elif (timeout_counter % 15) == 0:   # every 3 sec
								#self.send_heartbeat(s)
								pass
								# Suppress Heartbeat for now
								#
								# Background: The spec and personal conversation
								# with Fred yielded that i-Telex uses Heartbeat
								# only until the printer has been started. After
								# that, only Acknowledge is used.
								#
								# Complications arise from the fact that some
								# services in the i-Telex network interpret
								# Heartbeat just like Acknowledge, i.e. printer is
								# started and printer buffer empty. Special case is
								# the 11150 service, which in the current version,
								# on receiving Heartbeat, sends a WRU whilst the
								# welcome banner is being printed, causing a
								# character jumble.


				except (socket.error,BrokenPipeError,ConnectionResetError):
					l.error("Exception caught:", exc_info = sys.exc_info())
					error = True
					break

		except (KeyboardInterrupt, SystemExit):
			l.info('Exit by Keyboard')
		
		# catch again because at time as the initial ack the connection can already be closed again
		except (socket.error,BrokenPipeError,ConnectionResetError):
			l.error("Exception caught:", exc_info = sys.exc_info())
			error = True
			break

		finally:
			if not is_ascii:
				# Don't send end packet in case of error. There may be two error
				# cases:
				# - Protocol error: We've already sent a reject package.
				# - Network error: There's no connection to send over anymore.
				if not error:
					self.send_end(s)
			l.info('end connection')

			# Freigeben der Semaphore beim Beenden des Prozesses
			try:
				sema.release()
			except Exception:
				pass




	def send_heartbeat(self, s):
		'''Send heartbeat packet (0)'''
		data = bytearray([0, 0])
		l.debug('Sending i-Telex packet: Heartbeat ({})'.format(display_hex(data)))
		s.sendall(data)


	def send_ack(self, s, printed:int):
		'''Send acknowledge packet (6)'''
		# As per i-Telex specs (r874), the rules for Acknowledge are:
		#
		# 1. SHOULDN'T be sent before either Direct Dial or Baudot Data have
		#    been received once (only if we're being called)
		# 2. SHOULDN'T be sent before printer is started
		# 3. MUST be sent once the teleprinter has been started
		#
		# No. 1 is achieved through self._connected; it is set to ST.CON_TP_REQ
		# once the condition is fulfilled.
		#
		# No. 2 is always fulfilled since the printer is started only after
		# condition 1, or is already running if we're the caller.
		#
		# No. 3 is handled as follows:
		# - Once the teleprinter's start confirmation is received, and No. 1 is
		#   fulfilled, the first Acknowledge is sent (only if we're being called).
		# - Acknowledge packets are sent with the number of printed characters
		#   as argument (self._received_counter - self.get_print_buf_len()) on the
		#   schedule below.
		#
		# The schedule is as follows. Basically, Acknowledge is sent if and
		# only if there are unprinted characters in the buffer, i.e.
		# self.get_print_buf_len() > 0, and is triggered by any one of the
		# following (as per spec):
		#
		# - After a 1 s sending break (NB we don't fulfil this exactly, but it
		#   should suffice)
		# - Acknowledge is received and sent_counter equals the packet's data
		#   field (i.e. the remote side has printed all sent characters)
		# - Baudot Data is received and self.get_print_buf_len() >= 16

		# What must teleprinter driver modules implement to enable proper
		# Acknowledge throttling?
		#
		# They should send the ESC-~ command in the following way:
		# - It must not be sent before the printer has been started
		# - It must be sent at least once when the printer has been started
		# - It should be sent about every 500 ms
		# - Payload is the current buffer length, i.e. the characters still
		#   waiting to be printed
		# - The command shouldn't be sent multiple times for the same payload

		data = bytearray([6, 1, printed & 0xff])
		l.debug('Sending i-Telex packet: Acknowledge ({})'.format(display_hex(data)))
#		try:
		s.sendall(data)
#		except (BrokenPipeError,ConnectionResetError):
#			pass


	def send_version(self, s):
		'''Send version packet (7)'''
		version = ReleaseInfo.release_itx_version
		send = bytearray([7, 0, ReleaseInfo.itelex_protocol_version])
		send.extend([ord(i) for i in version])
		if len(version) < 6:
			send.append(0)
		send[1] = len(send) - 2 # length
		l.debug('Sending i-Telex packet: Version ({})'.format(display_hex(send)))
		s.sendall(send)


	def send_direct_dial(self, s, dial:str):
		'''Send direct dial packet (1)'''
		l.info("Sending direct dial: {!r}".format(dial))
		data = bytearray([1, 1])   # Direct Dial
		ext = encode_ext_for_direct_dial(dial)
		data.append(ext)
		l.debug('Sending i-Telex packet: Direct dial ({})'.format(display_hex(data)))
		s.sendall(data)


	def send_data_ascii(self, s):
		'''Send ASCII data direct'''
		a = ''
		while self._tx_buffer and len(a) < 250:
			b = self._tx_buffer.pop(0)
			if b not in '<>°%':
				a += b
		data = a.encode('ASCII')
		l.debug('Sending non-i-Telex data: {} ({})'.format(repr(data), display_hex(data)))
		s.sendall(data)
		return len(data)


	def send_data_baudot(self, s, bmc):
		'''Send baudot data packet (2)'''
		data = bytearray([2, 0])
		while self._tx_buffer and len(data) < 42:
			a = self._tx_buffer.pop(0)
			bb = bmc.encodeA2BM(a)
			if bb:
				for b in bb:
					data.append(b)
		length = len(data) - 2
		data[1] = length
		l.debug('Sending i-Telex packet: Baudot data ({})'.format(display_hex(data)))
		s.sendall(data)
		return length


	def send_end(self, s):
		'''Send end packet (3)'''
		send = bytearray([3, 0])   # End
		l.debug('Sending i-Telex packet: End ({})'.format(display_hex(send)))
		try:   # socket can possible be closed by other side
			s.sendall(send)
		except:
			pass


	def send_end_with_reason(self, s, reason):
		'''Send end packet with reason (3), for centralex disconnect'''
		send = bytearray([3, len(reason)])   # End with reason
		send.extend([ord(i) for i in reason])
		l.debug(f'Sending i-Telex packet: End {reason} ({display_hex(send)})')
		try:   # socket can possible be closed by other side
			s.sendall(send)
		except:
			pass

	# Types of reject packets (see txDevMCP):
	#
	# - abs   line disabled
	# - occ   line occupied
	# - der   derailed: line connected, but called teleprinter not starting
	#         up
	# - na    called extension not allowed
	@staticmethod
	def send_reject(s, msg = "abs"):
		'''Send reject packet (4)'''
		send = bytearray([4, len(msg)])   # Reject
		send.extend([ord(i) for i in msg])
		l.debug('Sending i-Telex packet: Reject ({})'.format(display_hex(send)))
		l.info('Reject, reason {!r}'.format(msg))
		s.sendall(send)


	def send_connect_remote(self, s, number, pin):
		'''Send connect remote packet (0x81)'''
		# l.info("Sending connect remote")
		send = bytearray([129, 6])   # 81 Connect Remote
		# Number
		number = self._number.to_bytes(length=4, byteorder="little")
		send.extend(number)
		# TNS pin
		tns_pin = self._tns_pin.to_bytes(length=2, byteorder="little")
		send.extend(tns_pin)
		l.debug('Sending i-Telex packet: Connect Remote ({})'.format(display_hex(send)))
		s.sendall(send)


	def send_accept_call_remote(self, s):
		'''Send accept call remote packet (0x84)'''
		send = bytearray([132, 0])   # 84 Accept call remote
		l.debug('Sending i-Telex packet: Accept call remote ({})'.format(display_hex(send)))
		s.sendall(send)









