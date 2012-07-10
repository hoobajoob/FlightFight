import cgi
import datetime
import calendar
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.api import mail
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch
from bs4 import BeautifulSoup
from decimal import *
from string import *

class City(db.Model):
	shortName = db.StringProperty(multiline=False)
	longName = db.StringProperty(multiline=False)

class FlightEntry(db.Model):
	roundTrip = db.BooleanProperty()
	departCity = db.StringProperty(multiline=False)
	returnCity = db.StringProperty(multiline=False)
	departDate = db.DateTimeProperty()
	returnDate = db.DateTimeProperty()
	lowPrice = db.FloatProperty()
	dateCreated = db.DateTimeProperty(auto_now_add=True)
	
class FlightWatch(db.Model):
	roundTrip = db.BooleanProperty()
	departCity = db.StringProperty(multiline=False)
	returnCity = db.StringProperty(multiline=False)
	departDate = db.DateTimeProperty()
	returnDate = db.DateTimeProperty()
	lowPrice = db.FloatProperty()
	highPrice = db.FloatProperty()
	currentPrice = db.FloatProperty()
	targetPrice = db.FloatProperty()
	dateLeniency = db.IntegerProperty()
	author = db.UserProperty()
	active = db.BooleanProperty()
	dateModified = db.DateTimeProperty(auto_now_add=True)
	dateCreated = db.DateTimeProperty(auto_now_add=True)
	

class CronJob(webapp.RequestHandler):
	def get(self):	
		returns = 0
		
		for fw in FlightWatch.all():
			if fw.active:
				direction='onewaytravel'
				returnString = ''
				if fw.roundTrip:
					direction='returntravel'
					retMonth=list(calendar.month_abbr)[fw.returnDate.month]
					retDay=str(fw.returnDate.day)
					returnString = '&retMonth=' + retMonth + '&retDay=' + retDay + '&retTime='
				departCity=fw.departCity
				returnCity=fw.returnCity
				depMonth=list(calendar.month_abbr)[fw.departDate.month]
				depDay=str(fw.departDate.day)
				url = 'https://compras.volaris.mx/meridia?posid=C0WE&page=requestAirMessage_air&action=airRequest&realRequestAir=realRequestAir' + '&direction=' + direction + '&departCity=' + departCity + '&depMonth=' + depMonth + '&depDay=' + depDay + '&depTime=&returnCity=' + returnCity + '&ADT=1&CHD=0&INF=0&classService=CoachClass&actionType=nonFlex&flightType=1&language=en' + returnString
				#self.response.out.write("Fetching URL: " + url)
				resultPage = urlfetch.fetch(url)
				if resultPage.status_code == 200:
					page = str(resultPage.content)
					soup = BeautifulSoup(page)
					span = soup.findAll("span", {"class": "step2PricePoints "})
					lowPrice = None
					for i in range(0, len(span)):
						ps = str(span[i].contents[0]).strip()[1:]
						price = Decimal(ps)
						if lowPrice == None or price < lowPrice:
							lowPrice = price
							
					self.response.out.write('Lowest Price = ' + str(lowPrice))
					if lowPrice is not None:
						lowPrice = float(lowPrice)
						curYear = datetime.datetime.now().year
						fe = FlightEntry()
						fe.lowPrice = lowPrice
						fe.roundTrip = fw.roundTrip
						fe.departCity = departCity
						fe.returnCity = returnCity
						fe.departDate = datetime.datetime(curYear, list(calendar.month_abbr).index(depMonth.capitalize()), int(depDay))
						if fw.roundTrip:
							fe.returnDate = datetime.datetime(curYear, list(calendar.month_abbr).index(retMonth.capitalize()), int(retDay))
						fe.put()
						fw.currentPrice = lowPrice
						newEntry = fw.lowPrice is None
						if fw.lowPrice is None or lowPrice < fw.lowPrice:
							if not newEntry and fw.author.email() is not None:
								message = mail.EmailMessage()
								message.sender = "kc@recroomrecords.com"
								message.to = fw.author.email()
								message.subject = 'Flight-Fight Update - Price Decrease'
								message.body = 'Volaris Price Update:\n\nThe price of a monitored flight has gone DOWN!!\n\n Flight details:\n' + fw.departCity + ' to ' + fw.returnCity + ' on ' + str(fw.departDate) + '\nYour Target Price: ' + str(fw.targetPrice) + '\nCurrent Price: ' + str(lowPrice) + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
								message.send()
							fw.lowPrice = lowPrice
								
						if lowPrice > fw.highPrice:
							if not newEntry and fw.author.email() is not None:
								message = mail.EmailMessage()
								message.sender = "kc@recroomrecords.com"
								message.to = fw.author.email()
								message.subject = 'Flight-Fight Update - Price Increase'
								message.body = 'Volaris Price Update:\n\nThe price of a monitored flight has gone UP!!\n\n Flight details:\n' + fw.departCity + ' to ' + fw.returnCity + ' on ' + str(fw.departDate) + '\nYour Target Price: ' + str(fw.targetPrice) + '\nCurrent Price: ' + str(lowPrice) + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
								message.send()	
							fw.highPrice = lowPrice
						if newEntry and fw.author.email() is not None:
								message = mail.EmailMessage()
								message.sender = "kc@recroomrecords.com"
								message.to = fw.author.email()
								message.subject = 'Flight-Fight Update - New Flight Added'
								message.body = 'Volaris Flight Tracking:\n\nYou are now monitoring a new flight on Volaris!!\n\n Flight details:\n' + fw.departCity + ' to ' + fw.returnCity + ' on ' + str(fw.departDate) + '\nYour Target Price: ' + str(fw.targetPrice) + '\nCurrent Price: ' + str(lowPrice) + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
								message.send()	
						
						fw.dateModified = datetime.datetime.now()
						fw.put()
				else:
					self.response.out.write('Error Fetching URL Data')
		
class Predictive(webapp.RequestHandler):
	def get(self):
		cities = City.all()
		
		returns = 0
		
		for dep in cities:
	
			direction='onewaytravel'
			departCity=dep.shortName
			depMonth='JUN'
			depDay='30'
			returnCity='CUN'
			retMonth='JUN'
			retDay='30'
			
			url = 'https://compras.volaris.mx/meridia?posid=C0WE&page=requestAirMessage_air&action=airRequest&realRequestAir=realRequestAir' + '&direction=' + direction + '&departCity=' + departCity + '&depMonth=' + depMonth + '&depDay=' + depDay + '&depTime=&returnCity=' + returnCity + '&ADT=1&CHD=0&INF=0&classService=CoachClass&actionType=nonFlex&flightType=1&language=en' + '&retMonth=' + retMonth + '&retDay=' + retDay + '&retTime='
			resultPage = urlfetch.fetch(url)
			if resultPage.status_code == 200:
				page = str(resultPage.content)
				soup = BeautifulSoup(page)
				span = soup.findAll("span", {"class": "step2PricePoints"})
				lowPrice = None
				for i in range(0, len(span)):
					ps = str(span[i].contents[0]).strip()[1:]
					price = Decimal(ps)
					if lowPrice == None or price < lowPrice:
						lowPrice = price
						
				print 'Lowest Price = ' + str(lowPrice)
				if lowPrice is not None:
					curYear = datetime.datetime.now().year
					fe = FlightEntry()
					fe.lowPrice = float(lowPrice)
					fe.roundTrip = not direction == 'onewaytravel'
					fe.departCity = departCity
					fe.returnCity = returnCity
					fe.departDate = datetime.datetime(curYear, list(calendar.month_abbr).index(depMonth.capitalize()), int(depDay))
					fe.returnDate = datetime.datetime(curYear, list(calendar.month_abbr).index(retMonth.capitalize()), int(retDay))
					fe.put()
			else:
				print 'Error Fetching URL Data'
		print returns + ' returned values'
	
class Init(webapp.RequestHandler):
	def get(self):
		city = City()
		city.KeyName = "ACA"
		city.shortName = "ACA"
		city.longName = "Acapulco"
		city.put()
		
		city = City()
		city.KeyName = "AGU"
		city.shortName = "AGU"
		city.longName = "Aguascalientes"
		city.put()
		
		city = City()
		city.KeyName = "CUN"
		city.shortName = "CUN"
		city.longName = "Cancun"
		city.put()
		
		city = City()
		city.KeyName = "CUU"
		city.shortName = "CUU"
		city.longName = "Chihuahua"
		city.put()
		
		city = City()
		city.KeyName = "CLQ"
		city.shortName = "CLQ"
		city.longName = "Colima"
		city.put()
		
		city = City()
		city.KeyName = "CVJ"
		city.shortName = "CVJ"
		city.longName = "Cuernavaca"
		city.put()
		
		city = City()
		city.KeyName = "CUL"
		city.shortName = "CUL"
		city.longName = "Culican"
		city.put()
		
		city = City()
		city.KeyName = "GDL"
		city.shortName = "GDL"
		city.longName = "Guadalajara"
		city.put()
		
		city = City()
		city.KeyName = "HMO"
		city.shortName = "HMO"
		city.longName = "Hermosillo"
		city.put()
		
		city = City()
		city.KeyName = "LAP"
		city.shortName = "LAP"
		city.longName = "La Paz"
		city.put()		
		
		city = City()
		city.KeyName = "BJX"
		city.shortName = "BJX"
		city.longName = "Leon"
		city.put()		
		
		city = City()
		city.KeyName = "SJD"
		city.shortName = "SJD"
		city.longName = "Los Cabos"
		city.put()		
		
		city = City()
		city.KeyName = "LMM"
		city.shortName = "LMM"
		city.longName = "Los Mochis"
		city.put()		
		
		city = City()
		city.KeyName = "MZT"
		city.shortName = "MZT"
		city.longName = "Mazatlan"
		city.put()	
		
		city = City()
		city.KeyName = "MXL"
		city.shortName = "MXL"
		city.longName = "Mexicali"
		city.put()	
		
		city = City()
		city.KeyName = "MEX"
		city.shortName = "MEX"
		city.longName = "Mexico City"
		city.put()	
		
		city = City()
		city.KeyName = "MTY"
		city.shortName = "MTY"
		city.longName = "Monterrey"
		city.put()	
		
		city = City()
		city.KeyName = "MLM"
		city.shortName = "MLM"
		city.longName = "Morelia"
		city.put()
		
		city = City()
		city.KeyName = "OAX"
		city.shortName = "OAX"
		city.longName = "Oaxaca"
		city.put()
		
		city = City()
		city.KeyName = "PBC"
		city.shortName = "PBC"
		city.longName = "Puebla"
		city.put()
		
		city = City()
		city.KeyName = "PVR"
		city.shortName = "PVR"
		city.longName = "Puerto Vallarta"
		city.put()
		
		city = City()
		city.KeyName = "TIJ"
		city.shortName = "TIJ"
		city.longName = "Tijuana"
		city.put()
		
		city = City()
		city.KeyName = "TLC"
		city.shortName = "TLC"
		city.longName = "Toluca"
		city.put()
		
		city = City()
		city.KeyName = "UPN"
		city.shortName = "UPN"
		city.longName = "Uruapan"
		city.put()
		
		city = City()
		city.KeyName = "ZCL"
		city.shortName = "ZCL"
		city.longName = "Zacatecas"
		city.put()
		
		city = City()
		city.KeyName = "MDW"
		city.shortName = "MDW"
		city.longName = "Chicago / Midway"
		city.put()
		
		city = City()
		city.KeyName = "FAT"
		city.shortName = "FAT"
		city.longName = "Fresno"
		city.put()
		
		city = City()
		city.KeyName = "LAS"
		city.shortName = "LAS"
		city.longName = "Las Vegas"
		city.put()
		
		city = City()
		city.KeyName = "LAX"
		city.shortName = "LAX"
		city.longName = "Los Angeles"
		city.put()
		
		city = City()
		city.KeyName = "SAN"
		city.shortName = "SAN"
		city.longName = "San Diego"
		city.put()
		
		city = City()
		city.KeyName = "OAK"
		city.shortName = "OAK"
		city.longName = "Francisco / Oakland"
		city.put()
		
		city = City()
		city.KeyName = "SJC"
		city.shortName = "SJC"
		city.longName = "Jose California"
		city.put()

application = webapp.WSGIApplication([
  ('/cron', CronJob),
  ('/cron/init', Init)
], debug=True)


def main():
  run_wsgi_app(application)


if __name__ == '__main__':
  main()