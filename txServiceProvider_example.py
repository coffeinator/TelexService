#!/bin/env python3

import logging
l = logging.getLogger("txs." + __name__)

# if we were started as a program, then derive from debug class
# else from the normale base class
if __name__ == "__main__":
	from txServiceProvider_debug import TelexServiceProvider_debug as TxSP_base
else:
	from txServiceProvider_base import TelexServiceProvider_base as TxSP_base


class TelexServiceProvider(TxSP_base):

	def doHandleClient(self):
		# this will print a text on the teletype
		self.send('\r\nWelcome. Send data and it will be echoed back.\r\n')
		
		# while we are connected and not got SIGTERM
		while self.is_running():
		
			# example for reading input
			# (this is a little advanced one because with recvCorrLine() you can cancel an input if you had a typo.
			#  the return value will then be '')
		
			s = ''
			# ATTENTION! EVERY loop which expects an input MUST HAVE "self.is_running()" !
			# (else it would run unlimited in the loop!!!)
			while self.is_running() and len(s) == 0:
				self.send('Ask: ')
				s = self.recvCorrLine()
				# you can also print to normal output. But be aware: This want be written on the teletype.
#				print(s)
			
			
			# I needed the prior input behavior so much in my first project so I implemented this function:
#			s = self.getInput('Ask')
			self.send('Got: '+s+'\n')
		l.debug('Stopped or conn is closed.')


# for debugging you can start this module directly as program
try:
	if __name__ == "__main__":
		obj = TelexServiceProvider()
		obj.doHandleClient()
except KeyboardInterrupt:
	pass














