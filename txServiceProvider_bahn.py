#!/bin/env python3

"""
Service Provider Class for bahn auskunft
This provides a bahn auskunft to the i-telex network
"""

import requests
import time
from datetime import datetime

import sys

#import testjsons

#import os
#os.environ['NO_PROXY'] = '127.0.0.1'


import logging
l = logging.getLogger("txs." + __name__)
#import http.client as http_client
#http_client.HTTPConnection.debuglevel = 1

# You must initialize logging, otherwise you'll not see debug output.
#logging.basicConfig()
#logging.getLogger().setLevel(logging.DEBUG)
#requests_log = logging.getLogger("requests.packages.urllib3")
#requests_log.setLevel(logging.DEBUG)
#requests_log.propagate = True

if __name__ == "__main__":
	from txServiceProvider_debug import TelexServiceProvider_debug as TxSP_base
else:
	from txServiceProvider_base import TelexServiceProvider_base as TxSP_base

class TelexServiceProvider(TxSP_base):

	_stationsMaxHitSize = 10

	_baseurl = 'https://efa.vagfr.de/vagfr3/'
	#_baseurl = 'https://www.kvv.de/tunnelEfaDirect.php'

	_header = {
		"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
	}

	_base_params = {
		"outputFormat": "JSON",
		"stateless": 1,
#		"locationServerActive": 1,
		"coordOutputFormat": "WGS84[dd.ddddd]",
	}

	_params_sf = {
		"type_sf": "any",
		"anyMaxSizeHitlist": 10,
#		"anyObjFilter_sf": 2,
#		"w_regPrefAl": 2
	}

	_params_dm = {
		'type_dm': 'any',
		'useRealtime': 1,
		'mergeDep': 1,
		'useAllStops': 1,
		'mode': 'direct',
		'itOptionsActive': 1,
		'ptOptionsActive': 1,
		'imparedOptionsActive': 1,
		'depType': 'stopEvents',
		'maxTimeLoop': 2,
		'itdTripDateTimeDepArr': 'dep'
	}

	_params_trip = {
		'sessionID': 0,
		'requestID': 0,
		'command':'',
		'language': 'de',
#		'itdLPxx_useJs': 1,
		'std3_suggestMacro': 'std3_suggest',
		'std3_commonMacro': 'trip',
#		'itdLPxx_contractor': '',
		'std3_contractorMacro': '',
		
		'type_origin': 'any',
		'type_destination': 'any',
		'type_via': 'any',
		'type_notVia': 'any',
		
		'itOptionsActive': 1,
		'ptOptionsActive': 1,

		'useRealtime': 1,

#		'includedMeans': 'checkbox'
#		'inclMOT_0': 1,
#		'inclMOT_1': 1,
#		'inclMOT_2': 1,
#		'inclMOT_3': 1,
#		'inclMOT_4': 1,
#		'inclMOT_5': 1,
#		'inclMOT_6': 1,
#		'inclMOT_7': 1,
#		'inclMOT_8': 1,
#		'inclMOT_9': 1,
#		'inclMOT_10': 1,
#		'inclMOT_11': 1,
#		'inclMOT_12': 1,
#		'inclMOT_13': 1,
#		'inclMOT_14': 1,
#		'inclMOT_15': 1,
#		'inclMOT_16': 1,
#		'inclMOT_17': 1,
#		'inclMOT_18': 1,
#		'inclMOT_19': 1,
		
		# Maximaler Fußweg [in Minuten]
		'trITMOTvalue100': 10,
		
		'useProxFootSearch': 'on',
		'levelPTMm': 'mainconnection',
		
#		'dwellTimeMinutes': '',
#		'itdLPxx_snippet': 1,
#		'itdLPxx_template': 'tripresults_pt_trip',
#		'computationType': 'sequence',
		
		'calcNumberOfTrips': 5,
		'calcOneDirection': 1,

		'useProxFootSearch': 1,


		### SUCHPARAMETER ###

#		nameInfo_origin=
#		nameInfo_destination=7006418
#		nameInfo_via=invalid
#		nameInfo_notVia=invalid

#		itdTripDateTimeDepArr= dep | arr
#		itdDateDayMonthYear=19.10.2025
#		itdTime=17:21

		#zeitschnelle
		#wenige umstiege
		#kurze fusswege
		#verlaessliche
		#preisguenstige
#		routeType= LEASTTIME | LEASTINTERCHANGE | LEASTWALKING | RELIABLE | LEASTCOSTEX

		# nur nahverkehr = 403
#		lineRestriction= 400 | 403

#		changeSpeed=normal|fast|slow | [25..100..400] # (slow = 50, fast = 200)

		# fahrradmitnahme
#		trITMOTvalue102=15

#		'maxChanges': 9,
	}
	
	_params_trip_detail = {
		'outputFormat': 'JSON',
		'singleTripSelection': 'on',
		'singleTripSelector1': 'on',
		'language': 'de',
		'command': 'tripPathDesc:',
		'sessionID': '',
		'requestID': 0
#		'itdLPxx_tripDetail': 1
#		'itdLPxx_timeFormat': 
#		'itdLPxx_departNextDay': true
#		'itdLPxx_arriveNextDay': true
#		'itdLPxx_snippet': 1
#		'itdLPxx_template': tripDetail
	}
	
	_params_trip_prevnext = {
		'language': 'de',
#		'itdLPxx_template': 'tripresults_pt_trip',
#		'tdLPxx_timeFormat': '',
		'outputFormat': 'JSON',
#		'itdLPxx_snippet': 1,
#		'itdLPxx_noLoadingMessage': 1,
		'sessionID': '',
		'requestID': 0
	}

	def initOptions(self):
		self._startStation = None
		self._destStation = None
		self._viaStation = None
		self._notViaStation = None
		self._dateTimeDepArr = 'dep'		# dep | arr
		self._datetime = None
		self._lineRestriction = 400		# 400 | 403 (403 = nur nahverkehr
		self._routeType = 'LEASTTIME'	# LEASTTIME | LEASTINTERCHANGE | LEASTWALKING | RELIABLE | LEASTCOSTEX
		self._bicycle = 0				# fahrradmitnahme = 15
		self._changeSpeed = 100			# normal|fast|slow | [25..100..400] # (slow = 50, fast = 200)
		self._maxChanges = 9				# 0..9
	
	
	
	_dwellTime_via = 0
	_AlwaysDwellTimeJourneCalculation=1 # must be set if via is set
	_useAltOdv = 1
	
	_sessionID = 0
	_requestID = 0



	
	def ascii2tty(self,s):
		s = s.lower()
		s = s.replace('ä','ae')
		s = s.replace('ö','oe')
		s = s.replace('ü','ue')
		s = s.replace('ß','ss')
		s = s.replace('&',' und ')
		return s
	
	
	def __init__(self):
		super().__init__()
	
	def sendReqErr(self,status):
		self.send('ein verbindungsfehler ist aufgetreten. ('+str(status)+')\r\nversuchen sie es spaeter erneut.\r\n\n')


#	def reqGetStations2(sname):
#		return json_obj, 200
#		
#	def reqGetDepartures2():
#		return dep_json_obj, 200

	def reqGetStations(self,sname):
		rparams = self._base_params | self._params_sf | {"name_sf": sname}
		url = self._baseurl + "XSLT_STOPFINDER_REQUEST"
		#url = baseurl
		
		try:
			r = requests.get(url, params=rparams, headers=self._header)
		except:
			return None,600

		r.encoding = 'UTF-8'

		ret = None
		if r.status_code == 200:
			try:
				ret = r.json()
			except:
				pass

		return ret,r.status_code


	def reqGetDepartures(self):
	#	dt = time.localtime()
		rparams = self._base_params | self._params_dm | {
			"nameInfo_dm": self._startStation['id'],
			"itdDate":     time.strftime("%Y%m%d", self._datetime),
			"itdTime":     time.strftime("%H%M", self._datetime)
		}
		url = self._baseurl + "XSLT_DM_REQUEST"
		#url = baseurl
		
		try:
			r = requests.get(url, params=rparams, headers=self._header)
		except:
			return None,600

		r.encoding = 'UTF-8'

		ret = None
		if r.status_code == 200:
			try:
				ret = r.json()
			except:
				pass

		return ret,r.status_code

	def reqGetTrip(self):
		rparams = self._base_params | self._params_trip | {
			"nameInfo_origin":       self._startStation['id'],
			"nameInfo_destination":  self._destStation['id'],
			"itdTripDateTimeDepArr": self._dateTimeDepArr,
			"itdDate":               time.strftime("%Y%m%d", self._datetime),
			"itdTime":               time.strftime("%H%M",   self._datetime),
			"lineRestriction":       self._lineRestriction,
			"routeType":             self._routeType,
			"changeSpeed":           self._changeSpeed,
			"maxChanges":            self._maxChanges
		}
		if self._viaStation == None:
			rparams |= {
				"nameInfo_via": 'invalid',
			}
		else:
			rparams |= {
				"nameInfo_via": self._viaStation['id'],
				"dwellTime_via": self._dwellTime_via,
				"AlwaysDwellTimeJourneCalculation": 1, # must be set if via is set
				"useAltOdv": 1 # must be set if via is set
			}
		if self._notViaStation == None:
			rparams |= {
				"nameInfo_notVia": 'invalid',
			}
		else:
			rparams |= {
				"nameInfo_notVia": self._notViaStation['id'],
			}
		if self._bicycle > 0:
			rparams |= {"trITMOTvalue102": self._bicycle}
		
		url = self._baseurl + "XSLT_TRIP_REQUEST2"
		#url = baseurl
		
		try:
			r = requests.get(url, params=rparams, headers=self._header)
		except:
			return None,600

		r.encoding = 'UTF-8'

		ret = None
		if r.status_code == 200:
			try:
				ret = r.json()
			except:
				pass

		return ret,r.status_code

	def reqTripPrevNext(self,d):
		rparams = {}
		rparams |= self._params_trip_prevnext
		if d == 'f':
			rparams |= {'command': 'tripPrev'}
		elif d == 's':
			rparams |= {'command': 'tripNext'}
		else:
			return None,400
		rparams['sessionID'] = self._sessionID
		rparams['requestID'] = self._requestID
		
		url = self._baseurl + "XSLT_TRIP_REQUEST2"
		#url = baseurl
		
		try:
			r = requests.get(url, params=rparams, headers=self._header)
		except:
			return None,600

		r.encoding = 'UTF-8'

		ret = None
		if r.status_code == 200:
			try:
				ret = r.json()
			except:
				pass

		return ret,r.status_code

	def reqTripDetail(self,t):
		rparams = {}
		rparams |= self._params_trip_detail
		rparams['command']  += str(t)
		rparams['sessionID'] = self._sessionID
		rparams['requestID'] = self._requestID
		
		url = self._baseurl + "XSLT_TRIP_REQUEST2"
		#url = baseurl
		
		try:
			r = requests.get(url, params=rparams, headers=self._header)
		except:
			return None,600

		r.encoding = 'UTF-8'

		ret = None
		if r.status_code == 200:
			try:
				ret = r.json()
			except:
				pass

		return ret,r.status_code


	def getStationsFromJSON(self,stations_json):
		# isBest nach vorne stellen!
		tmp = {}
		if isinstance(stations_json['stopFinder']['points'], list):
			for p in stations_json['stopFinder']['points']:
				if p['anyType'] == 'stop':
					if not p['mainLoc'] in tmp.keys():
						tmp[p['mainLoc']] = []
					tmp[p['mainLoc']].append({'id':p['stateless'], 'loc': p['mainLoc'], 'name': p['object'], 'fullname': p['name']})
				if p['anyType'] == 'loc':
					if not p['name'] in tmp.keys():
						tmp[p['name']] = []
					tmp[p['name']].append({'id':p['stateless'], 'loc': p['name'], 'name': p['name'], 'fullname': p['name']})
			
			ret = []
			i = 1
			for l in tmp:        # for each location
				for p in tmp[l]: # for each point in location
					if i <= self._stationsMaxHitSize:
						ret.append({'lid': i}|p)
						i += 1
			return ret
		
		elif isinstance(stations_json['stopFinder']['points'], dict):
			p = stations_json['stopFinder']['points']['point']
			return [{
				'lid': 1,
				'id': p['stateless'],
				'loc': p['mainLoc'],
				'name': p['object'],
				'fullname': p['name']
			}]
		
		# eg points is None
		return None

	def getDeparturesFromJSON(self,dep_json):
		ret = {}
		ret['station'] = {
			'name': dep_json['dm']['points']['point']['object'],
			'loc' : '',
			'date': '{0:02d}.{1:02d}.{2}'.format(int(dep_json['dateTime']['day']),int(dep_json['dateTime']['month']),int(dep_json['dateTime']['year'])),
			'time': '{0:02d}:{1:02d}'.format(int(dep_json['dateTime']['hour']),int(dep_json['dateTime']['minute']))
		}
		if 'ref' in dep_json['dm']['points']['point'].keys():
			ret['station']['loc'] = dep_json['dm']['points']['point']['ref']['place']
		
		ret['deps'] = []
		
		for d in dep_json['departureList']:
			rappend = {
				'time': '{0:02d}:{1:02d}'.format(int(d['dateTime']['hour']),int(d['dateTime']['minute'])),
				'delay': '0',
				'type': d['servingLine']['motType'],
				'line': d['servingLine']['number'],
				'dest': d['servingLine']['direction'],
				'platform': d['platform'],
				'tripId': d['servingLine']['key'],
				'hasInfo': ('lineInfos' in d.keys())
			}
			if 'realDateTime' in d.keys() and 'realtimeTripStatus' in d.keys() and d['realtimeTripStatus'] == 'MONITORED':
				rappend['delay'] = d['servingLine']['delay']
			ret['deps'].append(rappend)
		self.send('')
		return ret



	def menuGetADateTime(self,prompt):
		self.send('format: dd.mm.yyyy hh:mm, hh:mm, oder \'j\' fuer jetzt\r\n')
		ts = ''
		while ts == '':
			ts = self.getInput(prompt)
			
			if ts == 'j':
				return time.localtime()
			elif len(ts) == 16:
				try:
					return time.strptime(ts, '%d.%m.%Y %H:%M')
				except:
					ts = ''
			elif len(ts) == 5:
				try:
					dt = time.localtime()
					return time.strptime(time.strftime("%d.%m.%Y",dt)+' '+ts, '%d.%m.%Y %H:%M')
				except:
					ts = ''
			else:
				ts = ''
		return None

	def menuGetStation(self,prompt):
		while True:
			stations = []
			sname = self.getInput(prompt)
			if sname == None:
				return None
			
			stations_json, status = self.reqGetStations(sname)
			if stations_json == None:
				self.sendReqErr(status)
				return None
			try:
				stations = self.getStationsFromJSON(stations_json)
			except Exception as e:
				self.send('fehler beim erstellen der liste der moeglichen stationen.\r\n')
#				print(sys.exc_info())
#				raise
				return None
			
			if stations == None:
				return None
			
			if len(stations) == 1:
				return stations[0]
			
			# print stations list
			self.send('\n')
			indentMax = len(str(len(stations)))+1
			cloc = ''
			for s in stations:
				if cloc != s['loc']:
					cloc = s['loc']
					self.send(self.ascii2tty(cloc)+'\r\n')
				indentCur = len(str(s['lid']))
				for i in range(0,(indentMax-indentCur)):
					self.send(' ')
				self.send(str(s['lid'])+': ')
				if s['fullname'].startswith(cloc):
					self.send(self.ascii2tty(s['name'])[:60])
				else:
					self.send(self.ascii2tty(s['fullname'])[:60])
				self.send('\r\n')
			self.send('\nbitte station auswaehlen. (x = neu suchen)\r\n')
			
			sid = ''
			iid = 0
			while sid == '':
				sid = self.getInput()
				
				if sid != 'x':
					try:
						iid = int(sid)
						if iid == 0 or iid > len(stations):
							sid = ''
					except:
						sid = ''
			
			if sid == '':
				return None
			if sid == 'x':
				continue
			else:
				for s in stations:
					if s['lid'] == iid:
						return s
		return None


	def menuPrintOptions(self):
		line = '1: '
		match self._lineRestriction:
			case 400: line += 'nah+fern'
			case 401: line += 'ohne ice'
			case 402: line += 'verbund ohne aufschlag'
			case 403: line += 'nur nah'       # verbund und nah
			case _:   line += 'art unbekannt'
		
		line += '. 2: '
		match self._routeType:
			case 'LEASTTIME':        line += 'zeitschnellste'
			case 'LEASTINTERCHANGE': line += 'wenige umstiege'
			case 'LEASTWALKING':     line += 'kurze fusswege'
			case 'RELIABLE':         line += 'verlaessliche'
			case 'LEASTCOSTEX':      line += 'preisguenstige'
		
		line += '. 3: '
		match self._bicycle:
			case 0: line += 'ohne'
			case _: line += 'mit'
		line += ' fahrrad.\r\n'
		self.send(line)
		
		line = '4: '
		if isinstance(self._changeSpeed,str):
			if self._changeSpeed == 'normal':
				line += 'normal'
			elif self._changeSpeed == 'slow':
				line += 'langsam'
			elif self._changeSpeed == 'fast':
				line += 'schnell'
		else:
			if (25 <= self._changeSpeed) and (self._changeSpeed < 37):       #  25   37
				line += 'sehr langsam'
			elif (37 <= self._changeSpeed) and (self._changeSpeed < 75):     #  50   75
				line += 'langsam'
			elif (75 <= self._changeSpeed) and (self._changeSpeed < 150):    # 100  150
				line += 'normal'
			elif (150 <= self._changeSpeed) and (self._changeSpeed < 300):   # 200  300
				line += 'schnell'
			elif (300 <= self._changeSpeed) and (self._changeSpeed <= 400):  # 400
				line += 'sehr schnell'
		
		line += ' gehen. 5: max. '
		line += str(self._maxChanges)
		line += ' umstiege.\r\n'
		self.send(line)
		
		line = '6: ueber '
		if (self._viaStation == None):
			line += '---'
		else:
			line += self._viaStation['fullname']
		line += '\r\n'
		self.send(line)
		
		line = '7: nicht ueber '
		if (self._notViaStation == None):
			line += '---'
		else:
			line += self._notViaStation['fullname']
		line += '\r\n'
		self.send(line)
	
	def menuDoOptionNahFern(self):
		self.send('1 = nah- und fernverkehr. 2 = ohne ice. 3 = nur nahverkehr\r\n')
		sel = self.getInputOption(['1','2','3'])
		match sel:
			case '1': self._lineRestriction = 400
			case '2': self._lineRestriction = 401
#			case '': self._lineRestriction = 402
			case '3': self._lineRestriction = 403
	
	def menuDoOptionOptimierung(self):
		self.send('1 = zeitschnellste. 2 = wenige umstiege. 3 = kurze fusswege\r\n')
		self.send('4 = verlaessliche.  5 = preisguenstige\r\n')
		sel = self.getInputOption(['1','2','3','4','5'])
		match sel:
			case '1': self._routeType = 'LEASTTIME'
			case '2': self._routeType = 'LEASTINTERCHANGE'
			case '3': self._routeType = 'LEASTWALKING'
			case '4': self._routeType = 'RELIABLE'
			case '5': self._routeType = 'LEASTCOSTEX'
	
	def menuDoOptionFahrrad(self):
		self.send('1 = ohne Fahrrad. 2 = mit Fahrrad\r\n')
		sel = self.getInputOption(['1','2'])
		match sel:
			case '1': self._bicycle =  0
			case '2': self._bicycle = 15
	
	def menuDoOptionGang_v(self):
		self.send('Gehgeschwindigkeit (25..400)\r\n')
		self.send('25=sehr langsam 50=langsam 100=normal 200=schnell 400=sehr schnell\r\n')
		v = 0
		while v == 0:
			sel = self.getInput()
			try:
				v = int(sel)
			except:
				v = 0
			if (25 <= v) and (v <= 400):
				self._changeSpeed = v
			else:
				v = 0
	
	def menuDoOptionUmstiege(self):
		self.send('maximalanzahl fuer umstiege (0 = direktverbindung .. 9 = beliebig)\r\n')
		sel = self.getInputOption(['0','1','2','3','4','5','6','7','8','9'])
		self._maxChanges = int(sel)
	
	def menuDoOptionVia(self):
		self.send('zwischenstation\r\n')
		self.send('1 = kein via. 2 = via auswaehlen.\r\n')
		sel = self.getInputOption(['1','2'])
		if sel == '1':
			self._viaStation = None
			self._dwellTime_via = 0
			
		else:
			station = None
			while station == None:
				station = self.menuGetStation('via')
			self._viaStation = station
			self.send('aufenthaltszeit (in minuten)\r\n')
			self._dwellTime_via = 0
			while self._dwellTime_via == 0:
				stime = self.getInput('zeit')
				try:
					itime = int(stime)
					if (0 < itime):
						self._dwellTime_via = itime
				except:
					pass
	
	def menuDoOptionNotVia(self):
		self.send('zwischenstation vermeiden\r\n')
		self.send('1 = keine. 2 = auswaehlen.\r\n')
		sel = self.getInputOption(['1','2'])
		if sel == '1':
			self._notViaStation = None
			
		else:
			station = None
			while station == None:
				station = self.menuGetStation('nicht via')
			self._notViaStation = station
			


	def getKuerzel4Type(self,t):
		try:
			ti = int(t)
			if ti in [0,13,14,15,16,18]:
				return 'z'
			if ti == 1:
				return 's'
			if ti == 2:
				return 'u'
			if ti in [3,4]:
				return 't'
			if ti in [5,6,7,17,19,21]:
				return 'b'
			if ti == 9:
				return 'w'
			if ti in [10,20]:
				return 'x'
			if ti == 12:
				return 'f'
			return ' '
		except:
			return ' '

	def getFillFromCode(self,c):
		try:
			ci = int(c)
			if ci < 0:
				return ' '
			if ci in [0,1,2,13]:
				return '-'
			if ci in [3,4]:
				return '.'
			if ci in [5,6,7,17,19,21]:
				return ' '
			if ci in [14,15,16]:
				return '='
			return ' '
		except:
			return ' '

	def prettyPrint_time(self,pdate='',ptime='',rdate='',rtime='',delay=''):
		ret = ptime
		
		if (rtime == '' and delay == '') or (ptime == rtime) or (delay == '0'):
			return ret+'    '
		try:
			if (rtime != '' and rdate == ''):
				t0 = datetime.strptime(ptime,  '%H:%M')
				t1 = datetime.strptime(rtime, '%H:%M')
				delay = str(int((t1-t0).total_seconds()/60))
			elif (rtime != '' and rdate != ''):
				t0 = datetime.strptime(pdate+' '+ptime,  '%d.%m.%Y %H:%M')
				t1 = datetime.strptime(rdate+' '+rtime, '%d.%m.%Y %H:%M')
				delay = str(int((t1-t0).total_seconds()/60))
			
			delay = '+'+delay
			for sc in range(0,4-len(delay)):
				ret += ' '
			return ret+delay
		except:
			return 'xx:xx    '

	def prettyPrint_duration(self,h,m):
		line = ''
		if h == 0:
			line += '   '
		else:
			if h < 10:
				line += ' '
			line += str(h) + 'h'
		line += ' '
		if m < 10:
			line += ' '
		line += str(m)+'min'
		return line

	def prettyPrint_departure(self,d):
		line = self.prettyPrint_time(ptime=d['time'],delay=d['delay'])
		
		line += '  '+self.getKuerzel4Type(d['type'])
		line += ' '+d['line']+'          '
		
		line = line[:22]
		line += ' '+self.ascii2tty(d['dest'])[:30]+'                                    '
		line = line[:59-len(d['platform'])-1]
		line += ' '+d['platform']
		
		if d['hasInfo']:
			line += '   (i)'
		
		self.send(line+'\r\n')
	
	def prettyPrint_departures(self,deps):
		self.send('\r\nabfahrten von '+self.ascii2tty(deps['station']['name']))
		if len(deps['station']['loc']) > 0:
			self.send(', '+self.ascii2tty(deps['station']['loc']))
		self.send('\r\n          ab  '+deps['station']['date']+' '+deps['station']['time']+' uhr\r\n\n');
		self.send('.zeit....art.linie.....ziel............................steig...i.\r\n')
		
#		print('                                                                 .')
		i = 0
		while i < 10 and i < len(deps['deps']):
			self.prettyPrint_departure(deps['deps'][i])
			i += 1
		self.send('\n')
	
	def prettyPrintDepLegend(self):
		self.send(' z = zug\r\n')
		self.send(' s = s-bahn\r\n')
		self.send(' u = u-bahn\r\n')
		self.send(' t = tram\r\n')
		self.send(' b = bus\r\n')
		self.send(' w = schiff\r\n')
		self.send(' x = taxi (ast/alt)\r\n')
		self.send(' f = flugzeug\r\n')
		self.send("' '= unbekannt\r\n")

	def prettyPrint_legs(self, legs):
		sumDur = 0
		sumWidth = 0
		foots = 0
		parts = []
		for l in legs:
			part = {
				'duration': int(l['timeMinute']),
				'min':  2,
				'max': 65,
				'cur': 2,
				'calced': False,
				'a': '(',
				'e': ')',
				'fill': self.getFillFromCode(l['mode']['code']),
				'type': '',
				'line': self.ascii2tty(l['mode']['number'])
			}
			
			if int(l['mode']['code']) < 0:
				# fussweg
				foots += 1
				part['type'] = 'f'
				part['line'] = ''
				part['a'] = part['e'] = ' '
				part['min'] = 3
				part['cur'] = 3
			
			elif (l['mode']['symbol'] == '') and 'trainType' in l['mode'].keys():
				part['type'] = self.ascii2tty(l['mode']['trainType'])
				part['line'] = self.ascii2tty(l['mode']['number'])
			
			else:
				tl = self.ascii2tty(l['mode']['number']).split(' ',1)
				part['type'] = tl[0]
				if len(tl) == 1:
					part['line'] = ''
				else:
					part['line'] = tl[1]

			if part['type'] != 'f':
				part['min'] += len(part['type'])

			fpBefore = None
			fpAfter  = None
			if 'footpath' in l.keys():
				for f in l['footpath']:
					if f['position'] == 'IDEST':
						continue
					sumDur += int(f['duration'])
					sumWidth += 3
					foots += 1
					fpath = {
						'duration': int(f['duration']),
						'min': 3,
						'max':65,
						'cur': 3,
						'calced': False,
						'e': ' ',
						'a': ' ',
						'fill': ' ',
						'type': 'f',
						'line': ''
					}
					if f['position'] == 'BEFORE':
						fpBefore = fpath
					if f['position'] == 'AFTER':
						fpAfter = fpath

			if fpBefore != None:
				parts.append(fpBefore)

			sumDur += part['duration']
			sumWidth += 2+len(part['type'])
			parts.append(part)
			
			if fpAfter != None:
				parts.append(fpAfter)

		maxW = 65
		if (sumWidth > maxW):
			sumWidth -= 2*foots
			for p in parts:
				if p['type'] == 'f':
					p['min'] = 1
					p['calcW'] = 1
			
		minWidths = 0
		minTimes  = 0
		for p in parts:
			calcW = maxW / sumDur * p['duration']
			if calcW < p['min']:
				p['calcW'] = p['min']
				p['calced'] = True
				minWidths += p['min']
				minTimes  += p['duration']
		
		restW = maxW - minWidths
		restT = sumDur - minTimes
		for p in parts:
			if not p['calced']:
				p['calcW'] = round(restW / restT * p['duration'])
				restW -= p['calcW']
				restT -= p['duration']

		ret = ''
		for p in parts:
			tla = ''
			tlm = ''
			tle = ''
			cw = p['calcW']
			
			l = len(p['type'])
			if l <= cw:
				tlm += p['type']
				cw -= l
			
			l = 2*len(p['a'])
			if l <= cw:
				tla += p['a']
				tle += p['e']
				cw -= l
			
			l = 1+len(p['line'])
			if l <= cw:
				tlm += ' '+p['line']
				cw -= l
			
			if 2 <= cw:
				tlm = ' '+tlm+' '
				cw -= 2
			
			fillhalbe = cw / 2
			filla = ''
			for i in range(0,int(fillhalbe)):
				filla += p['fill']
			fille = ''
			for i in range(0,round(fillhalbe)):
				fille += p['fill']
			
			ret += tla+filla+tlm+fille+tle
		
		return ret

	def prettyPrint_trips(self,trips_json):
		i = 0
		while i < len(trips_json['trips']):
			trip = trips_json['trips'][i]
			i += 1
			self.send('\n')
			line = ''
			line += str(i)+'.) '
			line += self.prettyPrint_time(pdate=trip['legs'][0]['points'][0]['dateTime']['date'],   ptime=trip['legs'][0]['points'][0]['dateTime']['time'],
			                              rdate=trip['legs'][0]['points'][0]['dateTime']['rtDate'], rtime=trip['legs'][0]['points'][0]['dateTime']['rtTime'])
			line += ' - '
			line += self.prettyPrint_time(pdate=trip['legs'][len(trip['legs'])-1]['points'][0]['dateTime']['date'],   ptime=trip['legs'][len(trip['legs'])-1]['points'][1]['dateTime']['time'],
			                              rdate=trip['legs'][len(trip['legs'])-1]['points'][0]['dateTime']['rtDate'], rtime=trip['legs'][len(trip['legs'])-1]['points'][1]['dateTime']['rtTime'])
			line += '  / '
			h,m = trip['duration'].split(':')
			line += self.prettyPrint_duration(int(h),int(m))
			line += '  /  '
			line += trip['interchange']
			line += ' umstiege'
			self.send(line)
			self.send('\r\n')
			
			line = ''
			line += self.ascii2tty(trip['legs'][0]['points'][0]['name']) + '                            '
			line = line[:30] + '  -  '
			dest = self.ascii2tty(trip['legs'][len(trip['legs'])-1]['points'][1]['name'])
			for j in range(0,30-len(dest)):
				line += ' '
			line += dest
			line = line[:65]
			self.send(line)
			self.send('\r\n')
			
			line = self.prettyPrint_legs(trip['legs'])
			self.send(line)
			self.send('\r\n')
		self.send('\n')

	def prettyPrint_stopPoint(self,point):
		line = ''
		line += self.prettyPrint_time(pdate=point['dateTime']['date'],  ptime=point['dateTime']['time'],
		                              rdate=point['dateTime']['rtDate'],rtime=point['dateTime']['rtTime'])
		line += ' : '
		line += self.ascii2tty(point['name'])[:35]
		line += '                                                                 '
		platf = ''
		if len(point['platformName']) > 0:
			platf += ' ('
			platf += self.ascii2tty(point['platformName'])
			platf += ')'
		line = line[:52-len(platf)]
		line += platf
		return line

	def menuPrintTripDetail(self,t):
		details_json,status = self.reqTripDetail(t)
		if details_json == None:
			self.sendReqErr(status)
			return
		
		trip = details_json['trips']['trip']
		self.send('\n')
		self.send('detailansicht ueber die verbindung ('+t+')\r\n')
		self.send('am '+trip['legs'][0]['points'][0]['dateTime']['date']+'\r\n')
		
		line = ' von '
		line += self.prettyPrint_time(pdate=trip['legs'][0]['points'][0]['dateTime']['date'],   ptime=trip['legs'][0]['points'][0]['dateTime']['time'],
		                              rdate=trip['legs'][0]['points'][0]['dateTime']['rtDate'], rtime=trip['legs'][0]['points'][0]['dateTime']['rtTime'])
		line += ' '
		line += self.ascii2tty(trip['legs'][0]['points'][0]['name'])[:35]
		line += '\r\n'
		self.send(line)
		
		line = '               ('
		h,m = trip['duration'].split(':')
		line += self.prettyPrint_duration(int(h),int(m))
		line += '  /  '
		line += trip['interchange']
		line += ' umstiege)\r\n'
		self.send(line)
		
		line = 'nach '
		line += self.prettyPrint_time(pdate=trip['legs'][len(trip['legs'])-1]['points'][0]['dateTime']['date'],   ptime=trip['legs'][len(trip['legs'])-1]['points'][1]['dateTime']['time'],
		                              rdate=trip['legs'][len(trip['legs'])-1]['points'][0]['dateTime']['rtDate'], rtime=trip['legs'][len(trip['legs'])-1]['points'][1]['dateTime']['rtTime'])
		line += ' '
		line += self.ascii2tty(trip['legs'][len(trip['legs'])-1]['points'][1]['name'])[:35]
		line += '\r\n'
		self.send(line)
		
		self.send('= = = = = = = = = = = = = = = = = = = = = = = = = =\r\n\n')
		
		for l in trip['legs']:
			
			# pathway BEFORE
			
			fpBefore = ''
			fpAfter = ''
			fpIdest = ''
			if 'footpath' in l.keys():
				for f in l['footpath']:
					line = ''
					h = int(int(f['duration'])/60)
					m = int(f['duration']) - h*60
					line += self.prettyPrint_duration(h,m)
					line += '     fussweg\r\n\n'
						
					if f['position'] == 'BEFORE':
						fpBefore = line
					if f['position'] == 'AFTER':
						fpAfter = line
					if f['position'] == 'IDEST':
						fpIdest = line

			self.send(fpBefore)
		
			if len(fpIdest) > 0:
				self.send(fpIdest)
				
			else:
				# 1st point
				
				line = self.prettyPrint_stopPoint(l['points'][0])
				line += '\r\n'
				self.send(line)
				
				# inbetween
			
				line = ''
				h = int(int(l['timeMinute'])/60)
				m = int(l['timeMinute']) - h*60
				line += self.prettyPrint_duration(h,m)
				line += ' :   '
				
				lineNo = self.ascii2tty(l['mode']['number'])
				
				if int(l['mode']['code']) < 0:
					# fussweg
					lineType = 'fussweg'
					lineNo = ''
				
				elif (l['mode']['symbol'] == '') and 'trainType' in l['mode'].keys():
					lineType = self.ascii2tty(l['mode']['trainType'])
					lineNo   = self.ascii2tty(l['mode']['number'])
				
				else:
					tl = self.ascii2tty(l['mode']['number']).split(' ',1)
					lineType = tl[0]
					if len(tl) == 1:
						lineNo = ''
					else:
						lineNo = tl[1]
				
				line += lineType
				if len(lineType) > 0 and len(lineNo) > 0:
					line += ' '
				line += lineNo
				
				line += ' - '
				line += self.ascii2tty(l['mode']['destination'])[:29]
				line += '\r\n'
				self.send(line)
				
				# info
				
				if 'infos' in l.keys() and l['infos'] != None:
					if isinstance(l['infos'],dict):
						line = '          : (i) '
						line += self.ascii2tty(l['infos']['info']['infoLinkText'])[:37]
						line += '\r\n'
						self.send(line)
					elif isinstance(l['infos'],list):
						for inf in l['infos']:
							line = '          : (i) '
							line += self.ascii2tty(inf['infoLinkText'])[:37]
							line += '\r\n'
							self.send(line)
				
				# 2nd point
				
				line = self.prettyPrint_stopPoint(l['points'][1])
				line += '\r\n\n'
				self.send(line)
			
			# pathway AFTER
			
			self.send(fpAfter)

		self.send('\n')


	def menuDoAbfahrt(self):
		self.send('abfahrtstafel gewaehlt.\r\n\n')
		
		station = None
		while station == None:
			station = self.menuGetStation('station')
		self._startStation = station
		
		self.send('\r\n')
		self._datetime = self.menuGetADateTime('zeit')
		if self._datetime == None:
			return
		
		departures_json, status = self.reqGetDepartures()
		if departures_json == None:
			self.sendReqErr(status)
			return None
		try:
			deps = self.getDeparturesFromJSON(departures_json)
		except:
			self.send('fehler beim erstellen der abfahrtsliste.\r\n\n')
			return None
		
		self.prettyPrint_departures(deps)
		self.send('legende drucken? ')
		o = self.getInputOption(['j','n'],prompt='j/n',end=' ')
		if o == 'j':
			self.prettyPrintDepLegend()
		self.send('\n')

	def menuDoVerbindungsManagement(self):
		trips_json, status = self.reqGetTrip()
		
		valids = ['s','f']
		printConns = True
		while True:
		
			if trips_json == None:
				self.sendReqErr(status)
				return None
	#		print(trips_json)

			if printConns:
		#		print('                                                                 .')
				if trips_json['trips'] == None:
					self.send('keine verbindungen gefunden.\r\n\n')
					return None

				for pa in trips_json['parameters']:
					if pa['name'] == 'sessionID':
						self._sessionID = pa['value']
					if pa['name'] == 'requestID':
						self._requestID = pa['value']

				self.send('\r\ngefundene verbindungen ')
				dt = trips_json['dateTime']
				self.send('{:02d}.{:02d}.{:04d}'.format(int(dt['day']),int(dt['month']),int(dt['year'])))
				self.send(' ab ' if dt['deparr'] == 'dep' else ' an ')
				self.send('{:02d}:{:02d}'.format(int(dt['hour']),int(dt['minute'])))
				self.send('\r\n')

				self.prettyPrint_trips(trips_json)
				self.send('\n')
				
				
				self.send('d.. = details fuer gewaehlte verbindung .\r\n')
				self.send('s = spaeter. f = frueher. x = zurueck.\r\n') # r x= retour.\r\n')
				
				valids = ['s','f','x']
				for i in range(0,len(trips_json['trips'])):
					valids.append('d'+str(i+1))
			
			printConns = True
			sel = self.getInputOption(valids,'verbindungen')
			
			if sel == 'x' or sel == '':
				return
			if sel == 's':
				trips_json, status = self.reqTripPrevNext('s')
			if sel == 'f':
				trips_json, status = self.reqTripPrevNext('f')
			if sel == 'r':
#				trips_json, status = self.reqTripPrevNext('r')
				self.send('not implemented yet.\r\n')
			
			if sel[0] == 'd':
				t = sel[1:]
				self.menuPrintTripDetail(t)
				printConns = False
	

	def menuDoVerbindung(self):
		self.send('verbindung gewaehlt.\r\n\n')
		
		if self._startStation != None:
			self.send('start-station: ' + self.ascii2tty(self._startStation['fullname']))
			self.send('\r\nbeibehalten? ')
			o = self.getInputOption(['j','n'],prompt='j/n',end=' ')
			if o == 'n':
				self._startStation = None
		
		if self._startStation == None:
			station = None
			while station == None:
				station = self.menuGetStation('start-station')
#			station = {'id':6930100} # bertoldsbrunnen
			self._startStation = station
		
		
		if self._destStation != None:
			self.send('ziel-station: ' + self.ascii2tty(self._destStation['fullname']))
			self.send('\r\nbeibehalten? ')
			o = self.getInputOption(['j','n'],prompt='j/n',end=' ')
			if o == 'n':
				self._destStation = None
		
		if self._destStation == None:
			station = None
			while station == None:
				station = self.menuGetStation('ziel-station')
#			station = {'id':7006418} # elchesheim grüner baum
			self._destStation = station
		
		
		if self._datetime != None:
			self.send('abfahrt' if self._dateTimeDepArr == 'dep' else 'ankunft')
			self.send(' '+time.strftime("%d.%m.%Y %H:%M", self._datetime))
			self.send('\r\nbeibehalten? ')
			o = self.getInputOption(['j','n'],prompt='j/n',end=' ')
			if o == 'n':
				self._datetime = None
		
		if self._datetime == None:
			self.send('\nab = abfahrtszeit oder an = ankunftszeit\r\n')
			depoarr = self.getInputOption(['abfahrt','ankunft'])
			self._dateTimeDepArr = 'dep' if depoarr == 'abfahrt' else 'arr'
			self._datetime = self.menuGetADateTime('zeit '+('ab' if self._dateTimeDepArr == 'dep' else 'an'))
			if self._datetime == None:
				return
		
		self.send('\r\n')
		
		sel = ''
		self.send('s = abfrage starten. o = optionen. (1-7) = option anpassen.\r\n')
		while sel != 's' and sel != 'x':
			sel = self.getInputOption(['s','o','x','1','2','3','4','5','6','7'],'optionen')
			
			match sel:
				case 'o': self.menuPrintOptions()
				case '1': self.menuDoOptionNahFern()
				case '2': self.menuDoOptionOptimierung()
				case '3': self.menuDoOptionFahrrad()
				case '4': self.menuDoOptionGang_v()
				case '5': self.menuDoOptionUmstiege()
				case '6': self.menuDoOptionVia()
				case '7': self.menuDoOptionNotVia()

		if sel == 's':
			self.menuDoVerbindungsManagement()
		if sel == 'x':
			self.send('abgebrochen\r\n')


	def doHandleClient(self):
		self.send("\r\nbahn-auskunft   v0.2\r\neingaben bestaetigen mit (neue zeile)\r\neingaben loeschen mit xxx am ende\r\n\n")
		
		self.send(self.WRU)
#		self.ignoreWRU = True
		owru = self.requestWRU()
#		print(owru)
		l.info(owru)
		
		self.send('\r\n\n')
		
		mode = ''
		ctn = 0
		while mode != 'x':
			self.send('a = abfahrtstafel. v = verbindung suchen.')
			if ctn > 0:
				self.send('\r\nvo = verbindung suchen, optionen behalten.')
			self.send(' x = trennen.\r\n')
			if ctn == 0:
				mode = self.getInputOption(['a','v','x'])
			else:
				mode = self.getInputOption(['a','v','vo','x'])
			
			try:
				if mode == 'a':
					self.menuDoAbfahrt()
				if mode == 'v':
					self.initOptions()
					self.menuDoVerbindung()
					ctn += 1
				if mode == 'vo':
					self.menuDoVerbindung()
			except:
				self.send('\r\nein schwerwiegender fehler ist aufgetreten.\r\n\n')
				raise



try:
	if __name__ == "__main__":
		obj = TelexServiceProvider()
		obj.doHandleClient()
except KeyboardInterrupt:
	pass














