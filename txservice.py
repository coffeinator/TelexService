#!/bin/env python3
"""
Telex Service Server based on piTelex project
"""

import socket
import multiprocessing
import signal
import sys
import os
import datetime
import threading

import logging
l = logging.getLogger("txs." + __name__)
import logging.handlers
import traceback

from argparse import ArgumentParser
from configparser import ConfigParser
import importlib

import txServiceProvider_base as txss_base

LOGLVL = { 'NOTSET' : 0 , 'DEBUG' : 10 , 'INFO' : 20 , 'WARN' : 30 , 'ERROR' : 40 , 'CRITICAL' : 50 }

config = None
configFile = 'txservice.conf'
cfg_defaults = {
	'server': {
		'port': 20260,
		'maxConcurrent': 10, # maximum of concurrent connections
		'maxWaiting': 2       # maximum number of connections can wait to be handled
	},
	'provider': {
		'module': 'txServiceProvider_base', # name of the handler provider module
		'WRU': '12345 duserv d'             # WRU of this service
	},
	'logging': {
		'level': 'INFO'
	}
}

TxSProvider = None

def init():
	global config,cfg_defaults,configFile,TxSProvider
	parser = ArgumentParser(prog='txservice',description='Provides an service to the i-telex network.',epilog='More infos at https://github.com/fablab-wue/piTelex.git')
	parser.add_argument("-c", "--config",
	    dest="cfg_file", default='txservice.conf', metavar="FILE",
	    help="Load config file (txservice.conf)")
	parser.add_argument("-p", "--port",
	    dest="port", metavar="PORT",
	    help="Listen to port PORT")
	parser.add_argument("--conn",
	    dest="max_conn", metavar="MAX_CONN",
	    help="Maximum of concurrent connections")
	parser.add_argument("-k", "--id", "--KG", "--wru",
	    dest="wru", metavar="ID",
	    help="WRU id of this service")
	parser.add_argument("-m", "--module",
	    dest="module", metavar="MODULE",
	    help="Python module with provider")
	parser.add_argument("-l", "--loglevel",
	    dest="loglvl", metavar="LEVEL",
	    help="Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)")
	
	args = parser.parse_args()
	
	# set config file from arguments
	if args.cfg_file is not None: configFile = args.cfg_file
	try:
		config = ConfigParser(cfg_defaults)
		config.read_dict(cfg_defaults)
		if not os.path.isfile(configFile):
			raise Exception('Config file "'+configFile+'" not found!')
		config.read(configFile)
	except:
		print('Error in config-file.')
		raise

	# overwrite config with arguments (if they are changed from default)
	if args.port     is not None: config['server']['port']          = args.port
	if args.max_conn is not None: config['server']['maxConcurrent'] = args.max_conn
	if args.module   is not None: config['provider']['module']      = args.module
	if args.wru      is not None: config['provider']['WRU']         = args.wru
	if args.loglvl   is not None: config['logging']['level']        = args.loglvl
	
	
	# logging
	init_error_log("./",10,"DEBUG")
	
	# import specified provider
	mod = importlib.import_module(config['provider']['module'])
	if config['provider']['module'] == 'txServiceProvider_base':
		TxSProvider = mod.TelexServiceProvider_base
	else:
		TxSProvider = mod.TelexServiceProvider


'''
##### LOGGING #####
'''

# Path where this file is stored
try:
	OUR_PATH = os.path.dirname(os.path.realpath(__file__))
except NameError:
	# If __file__ is not defined, fall back to working directory; should be
	# close enough.
	OUR_PATH = os.getcwd()

class MonthlyRotatingFileHandler(logging.handlers.RotatingFileHandler):
	"""
	Custom Handler for a monthly rotated log file. Implementation based on
	original Python source code (CPython's Lib/logging/handlers.py).
	"""
	def __init__(self, filename, mode='a', encoding=None):
		# Disable maxBytes to ensure rolling over only on month change
		# Disable dbackupCount because it's not used
		# Disable delay to simplify overridden methods
		super().__init__(filename, mode=mode, maxBytes=0, backupCount=0, encoding=encoding, delay=False)

		# Initialise last year-month-stamp
		self.last_year_month = datetime.datetime.now().strftime("%Y-%m")

	def shouldRollover(self, record):
		current_year_month = datetime.datetime.now().strftime("%Y-%m")
		if self.last_year_month == current_year_month:
			return 0
		else:
			return 1

	def doRollover(self):
		if self.stream:
			self.stream.close()
			self.stream = None
		dfn = self.rotation_filename(self.baseFilename + "_" + self.last_year_month)
		self.last_year_month = datetime.datetime.now().strftime("%Y-%m")
		if os.path.exists(dfn):
			os.remove(dfn)
		self.rotate(self.baseFilename, dfn)
		self.stream = self._open()

	def rotate(self, source, dest):
		if os.path.exists(source):
			os.rename(source, dest)


"""
def find_rev() -> str:
	# Try finding out the git commit id and return it.
	import subprocess
	result = subprocess.run(["git", "log", "--oneline", "-1"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True)
	return result.stdout.decode("utf-8", errors="replace").strip()
"""


def init_error_log(log_path, log_lvl, log_lvl_str):
	"""
	Initialise error logging, i.e. create the root logger. It saves all logged
	information in a monthly rotating file inside the path given. If the latter
	is relative, it's interpreted relative to where this Python file is stored.

	This is different from the log module, which implements a communication
	trace log (i.e. it logs the data read from all piTelex modules).

	Install handlers for uncaught exceptions.

	All piTelex modules should initialise their logging like so:

	>>> import logging
	>>> l = logging.getLogger("piTelex." + __name__)

	Calling l.warning et al. funnels all messages into the same log file of the
	root logger ("piTelex").
	"""
	logger = logging.getLogger("txs")
	logger.setLevel(log_lvl) # Log level of this root logger
	
	if not os.path.isabs(log_path):
		log_path = os.path.join(OUR_PATH, log_path)
	try:
		os.mkdir(log_path)
	except FileExistsError:
		pass
	handler = MonthlyRotatingFileHandler(filename = os.path.join(log_path, "txs-errors.log"))

	handler.setLevel(LOGLVL[config['logging']['level']]) # Upper bounds for log level of all loggers
	formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s]: %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	sys.excepthook = excepthook
	sys.unraisablehook = unraisablehook # Works from Python 3.8
	threading.excepthook = threading_excepthook
	
	logger.info(f"===== Telex Service Server =====")
	logger.info(f"log_lvl: {log_lvl} {log_lvl_str}")

def excepthook(etype, value, tb):
	to_log = "".join(traceback.format_exception(etype, value, tb))
	l.critical(to_log)
	print(to_log)

def unraisablehook(unraisable):
	excepthook(unraisable.exc_type, unraisable.exc_value, unraisable.exc_traceback)

def threading_excepthook(args):
	l.critical("Exception in Thread {}".format(args.thread))
	excepthook(args.exc_type, args.exc_value, args.exc_traceback)




'''
##### SERVER #####
'''

def main():
	# Graceful shutdown bei SIGINT/SIGTERM
	stop = multiprocessing.Event()
	acceptNew = True
	children = []
	# Semaphore zur Begrenzung paralleler Prozesse
	sema = multiprocessing.Semaphore(int(config['server']['maxConcurrent']))

	# stops all active connections and comes to an end
	def _signal_handler_term(signum, frame):
		l.info("Signal received, shutting down...")
		stop.set()
	# get count of currently connected connections
	def _signal_handler_getconn(signum, frame):
		print(int(config['server']['maxConcurrent']) - sema.get_value())
	# stop accepting new connection, so we can give active connections a chance
	# to get finished without be ended while do long requests
	def _signal_handler_stopaccept(signum, frame):
		l.info("Signal received, dont accept anymore...")
		nonlocal acceptNew
		acceptNew = False

	signal.signal(signal.SIGINT, _signal_handler_term)
	signal.signal(signal.SIGTERM, _signal_handler_term)
	signal.signal(signal.SIGUSR1, _signal_handler_getconn)
	signal.signal(signal.SIGUSR2, _signal_handler_stopaccept)


	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
		server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server_sock.bind(('0.0.0.0', int(config['server']['port'])))
		server_sock.listen(int(config['server']['maxWaiting']))
		server_sock.settimeout(2.0)  # Periodisch prüfen, ob gestoppt werden soll
		l.info(f"Server listening on port {config['server']['port']}, max {config['server']['maxConcurrent']} concurrent handlers")

		try:
			while not stop.is_set():
				try:
					conn, addr = server_sock.accept()
				except ConnectionAbortedError:
					l.info("Exception caught:", exc_info = sys.exc_info())
					continue
				except (socket.timeout, OSError):
					continue

				# Versuchen, Semaphore zu kaufen; wenn nicht sofort möglich, lehnen wir ab
				if not acceptNew or not sema.acquire(block=False):
					# Keine Kapazität: schließen und optional kurze Nachricht senden
					try:
						txss_base.TelexServiceProvider_base.send_reject(conn, "occ")
						conn.close()
					except:
						pass
					l.warning(f"Rejected connection from {addr}: max concurrent reached")
					continue

				else:
					txss = TxSProvider()
					txss.WRU = config['provider']['WRU']
					# Startprozess: übergibt sema (Semaphore ist ein Synchronisationsobjekt)
					p = multiprocessing.Process(target=txss.handle_client, args=(conn, addr, sema, stop), daemon=True)
					p.start()
					children.append(p)

					# Schließe die Server-Seite des Sockets im Elternprozess, damit fd richtig verwaltet wird
					try:
						conn.close()
					except Exception:
						pass

				# Aufräumen beendeter Kind-Prozesse
				alive = []
				for c in children:
					if c.is_alive():
						alive.append(c)
					else:
						c.join(timeout=0)
				children = alive

		finally:
			print("Closing server socket and terminating children...")
			try:
				server_sock.close()
			except Exception:
				pass
			# Signal an Kinder: hier beenden wir sie freundlich, dann hart
			for c in children:
				if c.is_alive():
					c.terminate()
			for c in children:
				c.join(timeout=1)

if __name__ == "__main__":
	init()
	main()

