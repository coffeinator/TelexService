'''
Debug-Class
In case of a provider is run directly this provides i/o from/to the command line.
'''



class TelexServiceProvider_debug():
	def is_running(self):
		return True
	
	def send(self,s):
		print(s,end='')

	def clearInputBuffer(self):
		return
	def getInputLen(self):
		return 0
	def getOutputLen(self):
		return 0
	def getLastBuZiMode(self):
		return '<'
		
	def requestWRU(self):
		return 'WRU was requested'

	def recvCorrLine(self):
		return input()

	def getInput(self, prompt = ''):
		inp = ''
		while self.is_running() and inp == '':
			if len(prompt) > 0:
				self.send(prompt+': ')
			inp = self.recvCorrLine().strip()
			self.send('\r')
		return inp

	def getInputOption(self, validOptions, prompt = ''):
		opt = ''
		while self.is_running() and (opt == '' or not opt in validOptions):
			if len(prompt) > 0:
				self.send(prompt+': ')
			opt = self.recvCorrLine().strip()
			self.send('\r')
		return opt
