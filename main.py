import os
import calendar
import urllib
import logging
import json
import utils
import re
import urllib, urllib2, Cookie

from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.api import urlfetch
from google.appengine.api import taskqueue
from google.appengine.api import oauth
from bs4 import BeautifulSoup
from datetime import datetime

from decimal import *
from string import *

providers = {
    'Google'   : 'www.google.com/accounts/o8/id', # shorter alternative: "Gmail.com"
    'Yahoo'    : 'yahoo.com',
    'MySpace'  : 'myspace.com',
    'AOL'      : 'aol.com',
    'MyOpenID' : 'myopenid.com',
    'Custom' : 'http://w2popenid.appspot.com/oidprovider'
    # add more here
}


class KeyValuePair:
    key = object
    value = object
    def __init__(self, inputKey, inputValue):
        self.key = inputKey
        self.value = inputValue

class Registration(db.Model):
    accountName = db.StringProperty()
    registrationId = db.StringProperty()

class City(db.Model):
    shortName = db.StringProperty(multiline=False)
    longName = db.StringProperty(multiline=False)
    associatedAirports = db.StringListProperty()

class transCity(db.Model):
    shortName = db.StringProperty(multiline=False)
    longName = db.StringProperty(multiline=False)
    associatedAirports = db.StringListProperty()

class FlightEntry(db.Model):
    roundTrip = db.BooleanProperty()
    departCity = db.StringProperty(multiline=False)
    returnCity = db.StringProperty(multiline=False)
    departDate = db.DateTimeProperty()
    returnDate = db.DateTimeProperty()
    lowPrice = db.FloatProperty()
    dateCreated = db.DateTimeProperty(auto_now_add=True)
    dollars = db.BooleanProperty()

class FlightWatch(db.Model):
    roundTrip = db.BooleanProperty()
    departCity = db.StringProperty(multiline=False)
    returnCity = db.StringProperty(multiline=False)
    departDate = db.DateTimeProperty()
    returnDate = db.DateTimeProperty()
    lowPrice = db.FloatProperty()
    highPrice = db.FloatProperty()
    currentPrice = db.FloatProperty()
    previousPrice = db.FloatProperty()
    targetPrice = db.FloatProperty()
    dateLeniency = db.IntegerProperty()
    airline = db.StringProperty(multiline=False)
    author = db.UserProperty()
    authorEmail = db.StringProperty()
    active = db.BooleanProperty()
    dateModified = db.DateTimeProperty(auto_now_add=True)
    dateCreated = db.DateTimeProperty(auto_now_add=True)
    dollars = db.BooleanProperty()
    
    def getTrend(self):
        if self.currentPrice < self.previousPrice:
            return 'down'
        if self.currentPrice > self.previousPrice:
            return 'up'
        return 'neutral'
    
    def getActiveForCheckbox(self):
        if self.active:
            return "checked"
        else:
            return ""
    
    def getDepartDateString(self):
        return self.departDate.strftime("%d %b, %Y")
    
    def getReturnDateString(self):
        return self.returnDate.strftime("%d %b, %Y")
    
    def getTargetPriceString(self):
        if self.targetPrice is None:
            return 'N/A'
        else:
            return '$' + str(Decimal(str(self.targetPrice)).quantize(Decimal('.01'), rounding=ROUND_UP))
    
    def getHighPriceString(self):
        if self.highPrice is None:
            return 'N/A'
        else:
            return '$' + str(Decimal(str(self.highPrice)).quantize(Decimal('.01'), rounding=ROUND_UP))
    
    def getLowPriceString(self):
        if self.lowPrice is None:
            return 'N/A'
        else:
            return '$' + str(Decimal(str(self.lowPrice)).quantize(Decimal('.01'), rounding=ROUND_UP))
    
    def getCurrentPriceString(self):
        if self.currentPrice is None:
            return 'N/A'
        else:
            return '$' + str(Decimal(str(self.currentPrice)).quantize(Decimal('.01'), rounding=ROUND_UP))
   
    def getRemoveLink(self, label, baseURL):
        return '<a href="' + baseURL + '/remove?fwKey=' + str(self.key()) + '">' + label + '</a>';

    def getPurchaseLink(self):
        direction = 'onewaytravel'
        returnString = ''
        retMonth = ''
        retDay = ''
        depYear = '2012'
        retYear = '2012'
        if self.roundTrip:
            direction = 'returntravel'
            retMonth = list(calendar.month_abbr)[self.returnDate.month]
            retDay = str(self.returnDate.day)
            returnString = '&retMonth=' + retMonth + '&retDay=' + retDay + '&retTime='
        departCity = self.departCity
        returnCity = self.returnCity
        depMonth = list(calendar.month_abbr)[self.departDate.month]
        depDay = str(self.departDate.day)
        if self.airline == "Volaris":
            return '<a href="https://compras.volaris.mx/meridia?posid=C0WE&page=requestAirMessage_air&action=airRequest&realRequestAir=realRequestAir' + '&direction=' + direction + '&departCity=' + departCity + '&depMonth=' + depMonth + '&depDay=' + depDay + '&depTime=&returnCity=' + returnCity + '&ADT=1&CHD=0&INF=0&classService=CoachClass&actionType=nonFlex&flightType=1&language=en&rem1=FFLGTC' + returnString + '&utm_source=metasearch&utm_medium=deeplink&utm_content=FlightFight&utm_campaign=FlightFight" class="arefButton" target="_blank">Purchase</a>'
        elif self.airline == "AeroMexico":
            return '<form action="https://reservations.aeromexico.com/meridia" method="post" id="bBaf' + str(self.key()) + '" name="bBaf' + str(self.key()) + '" target="_blank">\
                        <div id="search_typetravel">\
                        <input type="hidden" name="posid" value="D5DE">\
                        <input type="hidden" name="page" value="ssw_SemiFlexOutboundMessage">\
                        <input type="hidden" name="action" value="SSWSemiFlexService">\
                        <input type="hidden" name="actionType" value="semiFlex">\
                        <input type="hidden" name="realRequestAir" value="realRequestAir">\
                        <input type="hidden" name="departCity" id="sector1_o" value="' + departCity + '"/>\
                        <input type="hidden" name="depMonth" id="depMonth" value="' + depMonth + '">\
                        <input type="hidden" name="depDay" id="depDay" value="' + depDay + '">\
                        <input type="hidden" name="depTime" id="depTime" value="anytime">\
                        <input type="hidden" name="returnCity" id="sector1_d" value="' + returnCity + '"/>\
                        <input type="hidden" name="retMonth" id="retMonth" value="' + retMonth + '">\
                        <input type="hidden" name="retDay" id="retDay" value="' + retDay + '">\
                        <input type="hidden" name="retTime" id="retTime" value="anytime">\
                        <input type="hidden" name="ADT" id="ft-adult" value="1">\
                        <input type="hidden" name="direction" id="direction" value="' + direction + '">\
                        <input type="submit" class="linkButton" value="Purchase" id="ft-submit" title="Click here to purchase your flight"/>\
                        </div>\
                    </form>'
        else:
            return ''
        
class URLOpener:
    def __init__(self):
        self.cookie = Cookie.SimpleCookie()
    
    def open(self, url, method, data = None):    
        while url is not None:
            response = urlfetch.fetch(url=url,
                            payload=data,
                            method=method,
                            headers=self._getHeaders(self.cookie),
                            allow_truncated=False,
                            follow_redirects=False,
                            deadline=60
                            )
            method = urlfetch.GET
            self.cookie.load(response.headers.get('set-cookie', '')) # Load the cookies from the response
            url = response.headers.get('location')
    
        return response
        
    def _getHeaders(self, cookie):
        headers = {
                    'Host' : 'www.google.com',
                    'User-Agent' : 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.2) Gecko/20090729 Firefox/3.5.2 (.NET CLR 3.5.30729)',
                    'Cookie' : self._makeCookieHeader(cookie)
                    }
        return headers

    def _makeCookieHeader(self, cookie):
        cookieHeader = ""
        for value in cookie.values():
            cookieHeader += "%s=%s; " % (value.key, value.value)
        return cookieHeader
        
class Aero(webapp.RequestHandler):
    def process(self, direction, departCity, returnCity, depMonth, depDay, depYear, retMonth, retDay, retYear):
        url = "https://reservations.aeromexico.com/meridia"
        form_fields = {
            "posid": "D5DE",
            "page": "ssw_SemiFlexOutboundMessage",
            "action": "SSWSemiFlexService",
            "actionType": "semiFlex",
            "realRequestAir": "realRequestAir",
            "departCity": departCity,
            "depMonth": depMonth,
            "depDay": depDay,
            "depYear": depYear,
            "depTime": "anytime",
            "returnCity": returnCity,
            "retMonth": retMonth,
            "retDay": retDay,
            "retYear": retYear,
            "retTime": "anytime",
            "direction": direction,
            "ADT": "1",
            "CHD": "0",
            "INF": "0"
        }
        
        form_data = urllib.urlencode(form_fields)
        
        try:
            resultPage = urlfetch.fetch(url=url, method=urlfetch.POST, payload=form_data, deadline=60)
            if resultPage.status_code == 200:
                lowPrice = None
                page = str(resultPage.content)
                soup = BeautifulSoup(page)
                tdIn = soup.findAll("span", {"class": "semiFlexAmt"})
                
                for i in tdIn:
                    price = float(i.contents[0].strip())
                    if lowPrice == None or price < lowPrice:
                        lowPrice = price
                        
                return lowPrice
         
        except urlfetch.DownloadError as err:
            print 'Error Fetching URL: ' + url + ' --- Error Type: ' + str(type(err)) + ' --- Error Args: ' + str(err.args) + ' --- Error Message: ' + str(err)
            return None
            
    def get(self):
        key = self.request.get("fwKey")
        if key != '':
            fw = FlightWatch.get(key)
            if fw is not None:
                url = "https://reservations.aeromexico.com/meridia"
                if fw.roundTrip:
                    direction = "returntravel"
                    returnMonth = list(calendar.month_abbr)[fw.returnDate.month]
                    returnDay = str(fw.returnDate.day)
                else:
                    direction = "onewaytravel"
                    returnMonth = ''
                    returnDay = ''
                form_fields = {
                    "posid": "D5DE",
                    "page": "ssw_SemiFlexOutboundMessage",
                    "action": "SSWSemiFlexService",
                    "actionType": "semiFlex",
                    "realRequestAir": "realRequestAir",
                    "departCity": fw.departCity,
                    "depMonth": list(calendar.month_abbr)[fw.departDate.month],
                    "depDay": str(fw.departDate.day),
                    "depYear": "2012",
                    "depTime": "anytime",
                    "returnCity": fw.returnCity,
                    "retMonth": returnMonth,
                    "retDay": returnDay,
                    "retYear": "2012",
                    "retTime": "anytime",
                    "direction": direction,
                    "ADT": "1",
                    "CHD": "0",
                    "INF": "0"
                }
                
                form_data = urllib.urlencode(form_fields)
                
                try:
                    print 'Fetching url: ' + url
                    #resultPage = urlfetch.fetch(url=url, method=urlfetch.POST, payload=form_data, deadline=60)
                    resultPage = URLOpener().open(url, urlfetch.POST, form_data)
                    if resultPage.status_code == 200:
                        self.response.out.write(resultPage.content)
                    else:
                        print 'Error Fetching URL: ' + url
                     
                 
                except urlfetch.DownloadError as err:
                    print 'Error Fetching URL: ' + url + ' --- Error Type: ' + str(type(err)) + ' --- Error Args: ' + str(err.args) + ' --- Error Message: ' + str(err)
            else:
                print 'Error Fetching URL: ' + url
                
class Southwest(webapp.RequestHandler):
    def process(self, fw):
        url = "http://www.southwest.com/flight/search-flight.html?int=HOMEQBOMAIR"
        
        if fw.roundTrip:
            direction = "RoundTrip"
            returnMonth = list(calendar.month_abbr)[fw.returnDate.month]
            returnDay = str(fw.returnDate.day)
            returnYear = str(fw.returnDate.year)
        else:
            direction = ""
            returnMonth = ''
            returnDay = ''
            returnYear = ''
        

        form_fields = {
            "ss": "0",
            "fareType": "DOLLARS",
            "disc": "",
            "submitButton": "",
            "previouslySelectedBookingWidgetTab": "",
            "originAirportButtonClicked": "no",
            "destinationAirportButtonClicked": "no",
            "formToken": "",
            "toggle_selfltnew": "",
            "toggle_AggressiveDrawers": "",
            "returnAirport": direction,
            "originAirport": fw.departCity,
            "destinationAirport": fw.returnCity,
            "outboundDateString": str(fw.departDate.month) + "/" + str(fw.departDate.day) + "/" + str(fw.departDate.year),
            "outboundTimeOfDay": "ANYTIME",
            "returnDateString": returnMonth + "/" + returnDay + "/" + returnYear,          
            "outboundTimeOfDay": "ANYTIME",
            "adultPassengerCount": "1",
            "seniorPassengerCount": "0"
        }
                
        form_data = urllib.urlencode(form_fields)
        
        try:
            resultPage = urlfetch.fetch(url=url, method=urlfetch.POST, payload=form_data, deadline=60)
            if resultPage.status_code == 200:
                lowPrice = None
                page = str(resultPage.content)
                soup = BeautifulSoup(page)
                tdIn = soup.findAll("input", {"id": re.compile('*QA\b')})
                
                for i in tdIn:
                    ns = i.nextSibling
                    ns = ns.nextSibling
                    
                    price = float(i.contents[0].strip())
                    if lowPrice == None or price < lowPrice:
                        lowPrice = price
                        
                return lowPrice
         
        except urlfetch.DownloadError as err:
            print 'Error Fetching URL: ' + url + ' --- Error Type: ' + str(type(err)) + ' --- Error Args: ' + str(err.args) + ' --- Error Message: ' + str(err)
            return None            
    def get(self):
        key = self.request.get("fwKey")
        if key != '':
            fw = FlightWatch.get(key)
            if fw is not None:
                url = "http://www.southwest.com/flight/search-flight.html?int=HOMEQBOMAIR"
        
                if fw.roundTrip:
                    direction = "RoundTrip"
                    returnMonth = list(calendar.month_abbr)[fw.returnDate.month]
                    returnDay = str(fw.returnDate.day)
                    returnYear = str(fw.returnDate.year)
                else:
                    direction = ""
                    returnMonth = ''
                    returnDay = ''
                    returnYear = ''
                
        
                form_fields = {
                    "ss": "0",
                    "fareType": "DOLLARS",
                    "disc": "",
                    "submitButton": "",
                    "previouslySelectedBookingWidgetTab": "",
                    "originAirportButtonClicked": "no",
                    "destinationAirportButtonClicked": "no",
                    "formToken": "",
                    "toggle_selfltnew": "",
                    "toggle_AggressiveDrawers": "",
                    "returnAirport": direction,
                    "originAirport": fw.departCity,
                    "destinationAirport": fw.returnCity,
                    "outboundDateString": str(fw.departDate.month) + "/" + str(fw.departDate.day) + "/" + str(fw.departDate.year),
                    "outboundTimeOfDay": "ANYTIME",
                    "returnDateString": returnMonth + "/" + returnDay + "/" + returnYear,          
                    "outboundTimeOfDay": "ANYTIME",
                    "adultPassengerCount": "1",
                    "seniorPassengerCount": "0"
                }
                        
                form_data = urllib.urlencode(form_fields)
                
                try:
                    print 'Fetching url: ' + url
                    #resultPage = urlfetch.fetch(url=url, method=urlfetch.POST, payload=form_data, deadline=60)
                    resultPage = URLOpener().open(url, urlfetch.POST, form_data)
                    
                    if resultPage.status_code == 200:
                        lowPrice = None
                        page = str(resultPage.content)
                        soup = BeautifulSoup(page)
                        #tdIn = soup.findAll("input", id=re.compile('QA$'))
                        tdIn = soup.findAll("div", {"class": "prduct_info"})

                        for i in tdIn:
                            self.response.out.write('</br>new')
                            ns = i.nextSibling
                            ns = ns.nextSibling
                            self.response.out.write(ns.contents[0])
                        #print resultPage.content
                        print form_data
                    else:
                        print 'Error Fetching URL: ' + url
                     
                 
                except urlfetch.DownloadError as err:
                    print 'Error Fetching URL: ' + url + ' --- Error Type: ' + str(type(err)) + ' --- Error Args: ' + str(err.args) + ' --- Error Message: ' + str(err)
            else:
                print 'Error Fetching URL: ' + url
                                  
                    
class Home(webapp.RequestHandler):
    def get(self):
        curLocale = 'en'
        if self.request.get("locale"):
            curLocale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            curLocale = self.request.headers['Accept-Language'][0:2]
        
        if users.get_current_user():
            url_login = users.create_logout_url(self.request.uri)
            if curLocale == 'en':
                url_loginLinktext = 'Logout'
            else:
                url_loginLinktext = 'Salir'
        else:
            url_login = '/login'
            if curLocale == 'en':
                url_loginLinktext = 'Login'
            else:
                url_loginLinktext = 'Entrar'
            #self.redirect(users.create_login_url(self.request.uri))
        
        message = self.request.get("message");
        if message == '':
            if curLocale == 'en':
                message = 'Just fill and submit this form to start tracking the best price.'
            else:
                message = 'Just fill and submit this form to start tracking the best price.'
                
        if curLocale == 'en':
            departCityLabel = 'Depart City'
            departDateLabel = 'Depart Date'
            returnCityLabel = 'Return City'
            returnDateLabel = 'Return Date'
            welcomeLabel = 'Create Flight Watch'
            targetPriceLabel = 'Target Price'
            roundTripLabel = 'Round Trip'
            submitLabel = 'Submit'
        else:
            departCityLabel = 'Salidas'
            departDateLabel = 'Fecha de salida'
            returnCityLabel = 'Retornos'
            returnDateLabel = 'Fecha de retornos'
            welcomeLabel = 'Crear Flight Watch'
            targetPriceLabel = 'Precio Meta'
            roundTripLabel = 'Redondo'
            submitLabel = 'Invia'
            
        cities = City.all()
        cities.order('longName')

        template_values = {
            'url_login': url_login,
            'url_loginLinktext': url_loginLinktext,
            'cities': cities,
            'locale': curLocale,
            'departCityLabel': departCityLabel,
            'departDateLabel': departDateLabel,
            'returnCityLabel': returnCityLabel,
            'returnDateLabel': returnDateLabel,
            'welcomeLabel': welcomeLabel,
            'targetPriceLabel': targetPriceLabel,
            'roundTripLabel': roundTripLabel,
            'submitLabel': submitLabel,
            'message': message
        }

        path = os.path.join(os.path.dirname(__file__), 'create.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        fw = FlightWatch()
        fw.roundTrip = self.request.get('roundTripCheckbox') == 'True'
        fw.departCity = self.request.get('departCityDropDown')
        fw.returnCity = self.request.get('returnCityDropDown')
        fw.departDate = datetime.strptime(self.request.get('departDatePicker'), '%d %B, %Y')
        if fw.roundTrip:
            fw.returnDate = datetime.strptime(self.request.get('returnDatePicker'), '%d %B, %Y')
        
        fw.targetPrice = float(self.request.get('targetPriceTextBox')[1:])
        fw.dateLeniency = 1
    
        fw.active = True
        fw.author = users.get_current_user()
        fw.put()
        
        if users.get_current_user():
            taskqueue.add(url='/newflightwatch', params={'fwKey': fw.key()})
            self.redirect('/overview?message=Successfully added Flight Watch')
        else:
            self.redirect('/login?fwKey=' + str(fw.key()))


class Feedback(webapp.RequestHandler):
    def get(self):
        locale = 'en'
        if self.request.get("locale"):
            locale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            locale = self.request.headers['Accept-Language'][0:2]
            
        
        if users.get_current_user():
            display = 'display:none'
            url_login = users.create_logout_url(self.request.uri)
            if locale == 'en':
                url_loginLinktext = 'Logout'
            else:
                url_loginLinktext = 'Salir'
        else:
            display = ''
            url_login = '/login'
            if locale == 'en':
                url_loginLinktext = 'Login'
            else:
                url_loginLinktext = 'Entrar'
        
        message = self.request.get("message");
        
        types = []
                
        if locale == 'en':
            emailLabel = 'Email Address'
            typeLabel = 'Feedback Type'
            typeDropDownLabel = 'Select Feedback Type'
            feedbackLabel = 'Feedback'
            welcomeLabel = 'Submit Feedback'
            submitLabel = 'Submit'
            types.append(KeyValuePair(1, 'Bug Report'))
            types.append(KeyValuePair(2, 'Feature Request'))
            types.append(KeyValuePair(3, 'Comment'))
        else:
            emailLabel = 'Email Address'
            typeLabel = 'Feedback Type'
            typeDropDownLabel = 'Select Feedback Type'
            feedbackLabel = 'Feedback'
            welcomeLabel = 'Submit Feedback'
            submitLabel = 'Invia'
            types.append(KeyValuePair(1, 'Bug Report'))
            types.append(KeyValuePair(2, 'Feature Request'))
            types.append(KeyValuePair(3, 'Comment'))

        template_values = {
            'url_login': url_login,
            'url_loginLinktext': url_loginLinktext,
            'types' : types,
            'locale': locale,
            'emailLabel': emailLabel,
            'typeLabel': typeLabel,
            'typeDropDownLabel': typeDropDownLabel,
            'feedbackLabel': feedbackLabel,
            'welcomeLabel': welcomeLabel,
            'submitLabel': submitLabel,
            'message': message,
            'display': display
        }

        path = os.path.join(os.path.dirname(__file__), 'feedback.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        if users.get_current_user():
            userEmail = users.get_current_user().email()
        else:
            userEmail = self.request.get('emailTextBox')
            
        try:
            message = mail.EmailMessage()
            message.sender = "kc@recroomrecords.com"
            message.to = "kc@recroomrecords.com"
            message.subject = 'Flight-Fight Feedback'
            message.body = 'Feedback Submitted from ' + userEmail + '\n\nType = ' + self.request.get('typeDropDown') + '\n\n' + self.request.get('feedbackTextbox')
            message.send()
        except:
            self.redirect('/feedback?message=Sorry, something broke.\nAn email was not sent with your feedback info, but it\'s probably in the error log.\n  We\'ll do our best to find it')
        else:
            self.redirect('/feedback?message=Feedback Submitted')

class About(webapp.RequestHandler):
    def get(self):
        locale = 'en'
        if self.request.get("locale"):
            locale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            locale = self.request.headers['Accept-Language'][0:2]
            
        
        if users.get_current_user():
            url_login = users.create_logout_url(self.request.uri)
            if locale == 'en':
                url_loginLinktext = 'Logout'
            else:
                url_loginLinktext = 'Salir'
        else:
            url_login = '/login'
            if locale == 'en':
                url_loginLinktext = 'Login'
            else:
                url_loginLinktext = 'Entrar'
        
        message = self.request.get("message");
                
        if locale == 'en':
            welcomeLabel = 'Welcome to Flight Fight'
            bodyMessage = "Flight Fight is an experimental project to monitor flight price changes for a specific \
                origin, destination and date combination, called a \'Flight Watch\'.</p>For now, Flight Fight uses a Google login for verification.  \
                There is also an accompanying Android App for viewing and entering Flight Watch items.  The most useful feature of the Android App \
                is the widget.  You can have a widget on your home screen for each Flight Watch you have created, which will give you constant status of \
                the current price, price trend and relation to your target price.  When a flight falls below your target price, you can choose to have the app \
                notify you by ringtone and vibrate, and when you acknowledge the notification, it will have a link to take you directly to purchase the ticket if you choose.  \
                </p>At this stage, Flight Fight only supports Volaris.  Future plans are to incorporate Aeromexico, European airlines, US and so on.  \
                </p>We are aware that, since this project is in its initial stages, there will be many improvements to be made.  Please use the \'Feedback\' page to provide any \
                feedback on bugs, feature requests or comments you may have.  When you\'re ready to start tracking flights and saving money, click the \'Create\' link above. \
                </p></p>Thank you for using Flight Fight."
        else:
            welcomeLabel = 'Bienvenidos a Pelea de Vuelos'
            bodyMessage = "Flight Fight is an experimental project to monitor flight price changes for a specific \
                origin, destination, and date combination, called a \'Flight Watch\'.</p>For now, Flight Fight uses a Google login for verification.  \
                There is also an accompanying Android App for viewing and entering Flight Watch items.  The most useful feature of the Android App \
                is the widget.  You can have a widget on your home screen for each Flight Watch you have created, which will give you constant status of \
                the current price, price trend and relation to your target price.  When a flight falls below your target price, you can choose to have the app \
                notify you by ringtone and vibrate, and when you acknowledge the notification, it will have a link to take you directly to purchase the ticket if you choose.  \
                </p>At this stage, Flight Fight only supports Volaris.  Future plans are to incorporate Aeromexico, European airlines, US and so on.  \
                </p>We are aware that, since this project is in its initial stages, there will be many improvements to be made.  Please use the \'Feedback\' page to provide any \
                feedback on bugs, feature requests or comments you may have.  When you\'re ready to start tracking flights and saving money, click the \'Create\' link above. \
                </p></p>Thank you for using Flight Fight."

        template_values = {
            'url_login': url_login,
            'url_loginLinktext': url_loginLinktext,
            'locale': locale,
            'bodyMessage': bodyMessage,
            'welcomeLabel': welcomeLabel,
            'message': message
        }

        path = os.path.join(os.path.dirname(__file__), 'main.html')
        self.response.out.write(template.render(path, template_values))


class Overview(webapp.RequestHandler):
    def get(self):
        locale = 'en'        
        if self.request.get("locale"):
            locale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            locale = self.request.headers['Accept-Language'][0:2]
        user = users.get_current_user();    
        if user:
            if self.request.get("fwKey"):
                fw = FlightWatch.get(self.request.get("fwKey"))
                if fw is not None:
                    fw.author = user
                    fw.authorEmail = user.email()
                    fw.put()
            url_login = users.create_logout_url(self.request.uri)
            if locale == 'en':
                url_loginLinktext = 'Logout'
            else:
                url_loginLinktext = 'Salir'
                
            message = self.request.get("message");
        
        
            flightWatches = []
            for fw in FlightWatch.all():
                if fw.author and fw.author == user:
                    flightWatches.append(fw)
                elif fw.authorEmail == user.email():
                        flightWatches.append(fw)
                    
                if locale == 'en':
                    titleLabel = 'Flight Watch Overview for ' + user.email()
                    activeLabel = "Active"
                    departCityLabel = 'Depart City'
                    departDateLabel = 'Depart Date'
                    destinationCityLabel = 'Return City'
                    returnDateLabel = 'Return Date'
                    targetPriceLabel = 'Target Price'
                    highPriceLabel = 'High Price'
                    lowPriceLabel = 'Low Price'
                    currentPriceLabel = 'Current Price'
                    purchaseLabel = 'Purchase Ticket'
                    submitLabel = 'Submit Changes'
                    hideInactiveLabel = 'Hide Inactive'
                    clearAllLabel = 'Clear All Filters'
                    airlineLabel = 'Airline'
                else:
                    titleLabel = 'Flight Watch Overview for ' + user.email()
                    activeLabel = "Activo"
                    departCityLabel = 'Salidas'
                    departDateLabel = 'Fecha de salida'
                    destinationCityLabel = 'Retornos'
                    returnDateLabel = 'Fecha de retornos'
                    targetPriceLabel = 'Precio Meta'
                    highPriceLabel = 'Precio Abajo'
                    lowPriceLabel = 'Precio Barato'
                    currentPriceLabel = 'Precio Ahorra'
                    purchaseLabel = 'Comprar Boleto'
                    submitLabel = 'Invia Cambios'
                    hideInactiveLabel = 'Hide Inactivos'
                    clearAllLabel = 'Clear All Filters'
                    airlineLabel = 'Linea'
        
                template_values = {
                    'url_login': url_login,
                    'url_loginLinktext': url_loginLinktext,
                    'flightWatches': flightWatches,
                    'titleLabel' : titleLabel,
                    'locale': locale,
                    'departCityLabel': departCityLabel,
                    'departDateLabel': departDateLabel,
                    'destinationCityLabel': destinationCityLabel,
                    'returnDateLabel': returnDateLabel,
                    'highPriceLabel': highPriceLabel,
                    'targetPriceLabel': targetPriceLabel,
                    'lowPriceLabel': lowPriceLabel,
                    'currentPriceLabel': currentPriceLabel,
                    'purchaseLabel': purchaseLabel,
                    'message': message,
                    'activeLabel' : activeLabel,
                    'submitLabel': submitLabel,
                    'hideInactiveLabel': hideInactiveLabel,
                    'clearAllLabel': clearAllLabel,
                    'airlineLabel' : airlineLabel
                }
        
            path = os.path.join(os.path.dirname(__file__), 'overview.html')
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/login')
           
    def post(self):
        activeList = self.request.get('activeResults').rsplit(",")
        for fwPair in activeList:
            key = fwPair.rsplit("|")[0]
            if key != '':
                fw = FlightWatch.get(key)
                if fw is not None:
                    if fwPair.rsplit("|")[1] == "true":
                        fw.active = True
                    else:
                        fw.active = False
                    fw.put()
            self.redirect('/overview?message=Successfully Updated Flight Watches')
        
        
        
class InsertFromAndroid(webapp.RequestHandler):
    def post(self):
        isError = False
        errorMessage = ''
        fw = FlightWatch()
        cuid = self.request.get('cuid')
        fw.departCity = self.request.get('departCity')
        fw.returnCity = self.request.get('returnCity')
        fw.departDate = datetime.strptime(self.request.get('departDate'), '%d %B, %Y')
        fw.targetPrice =  float(self.request.get('targetPrice'))
        fw.roundTrip = self.request.get('roundTrip') == 'true'
        if fw.roundTrip:
            fw.returnDate = datetime.strptime(self.request.get('returnDate'), '%d %B, %Y')
            
        fw.dateLeniency = 1
        if users.get_current_user():
            fw.author = users.get_current_user()
            fw.authorEmail = fw.author.email()
        else:
            fw.authorEmail = cuid
            
        if isError:
            self.response.out.write('Error:' + errorMessage)
        else:
            fw.active = True
            fw.put()
            taskqueue.add(url='/newflightwatch', params={'fwKey': fw.key()})
            self.response.out.write('successful');


class SendPush:
    def send(self, user, message):
        
        print '<html>'
        print '<head>'
        print '<title>'
        print 'Push'
        print '</title>'
        print '</head>'
        print '<body>'
        itemquery = db.GqlQuery("SELECT * FROM Registration WHERE accountName=:1",
                                user.email())
        items = itemquery.fetch(1)
        if len(items) > 0:
            registration = items[0]
            registrationId = registration.registrationId
            status = self.sendMessage(user.email(), registrationId, message)
            print '<p>Message sent, status: ' + status + '</p>'
        else:
            print '<p>No registration for ' + user.email() + '</p'
                    
        print '</body>'
        print '</html>'
        
    def sendMessage(self, accountName, registrationId, text):
        global collapse_key
        global server_account_name
        authToken = self.getAuthToken()
        if authToken == "":
            return "Cannot authenticate " + server_account_name 
        form_fields = {
            "registration_id": registrationId,
            "collapse_key": str(collapse_key),
            "data.message": text
        }
        logging.info("authToken: " + authToken)
        form_data = urllib.urlencode(form_fields)
        result = urlfetch.fetch(url="http://android.apis.google.com/c2dm/send",
                        payload=form_data,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded',
                                 'Authorization': 'GoogleLogin auth=' + authToken
                                })
        collapse_key = collapse_key + 1
        return result.content

    def getAuthToken(self):
        global server_account_name
        global server_account_password
        form_fields = {
            "accountType": "GOOGLE",
            "Email": server_account_name,
            "Passwd": server_account_password,
            "service": "ac2dm",
            "source": "mylifewithandroid-push-2.0"
        }
        form_data = urllib.urlencode(form_fields)
        result = urlfetch.fetch(url="http://www.google.com/accounts/ClientLogin",
                        payload=form_data,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'
                                })
        if result.status_code == 200:
            logging.info("Auth response: " + result.content)
            lines = result.content.split('\n')
            authToken = ""
            for line in lines:
                if line.startswith("Auth="):
                    authToken = line[5:len(line)]
            return authToken
        logging.error("error code: " + str(result.status_code) + "; error message: " + result.content)
        return ""
    
class FlightWatchUpdate:
    def process(self, fw, curLocale):
        if fw.active:
            if fw.departDate < datetime.now():
                fw.active = False
            else:
                direction = 'onewaytravel'
                returnString = ''
                retMonth = None
                retDay = None
                retYear = None
                if fw.roundTrip:
                    direction = 'returntravel'
                    retMonth = list(calendar.month_abbr)[fw.returnDate.month]
                    retDay = str(fw.returnDate.day)
                    retYear = str(fw.returnDate.year)
                    returnString = '&retMonth=' + retMonth + '&retDay=' + retDay + '&retYear='+ retYear + '&retTime='
                departCity = fw.departCity
                returnCity = fw.returnCity
                depMonth = list(calendar.month_abbr)[fw.departDate.month]
                depDay = str(fw.departDate.day)
                depYear = str(fw.departDate.year)
                
                aeroPrice = Aero().process(direction, departCity, returnCity, depMonth, depDay, depYear, retMonth, retDay, retYear)
                southwestPrice = Southwest().process(direction, departCity, returnCity, depMonth, depDay, depYear, retMonth, retDay, retYear)
                volarisPrice = None
                url = 'https://compras.volaris.mx/meridia?posid=C0WE&page=requestAirMessage_air&action=airRequest&realRequestAir=realRequestAir' + '&direction=' + direction + '&departCity=' + departCity + '&depMonth=' + depMonth + '&depDay=' + depDay + '&depTime=&returnCity=' + returnCity + '&ADT=1&CHD=0&INF=0&classService=CoachClass&actionType=nonFlex&flightType=1&language=en' + returnString
                #self.response.out.write("Fetching URL: " + url)
                try:
                    resultPage = urlfetch.fetch(url, deadline=30)
                    if resultPage.status_code == 200:
                        lowPrice = None
                        lowPriceRet = None
                        page = str(resultPage.content)
                        soup = BeautifulSoup(page)
                        tdIn = soup.findAll("td", {"id": re.compile('matrix_cal_body_fare1_.*_out')})
                        for i in tdIn:
                            spp = i.find("span", {"class": "step2PricePoints "})
                            ps = str(spp.contents[0]).strip()[1:str(spp.contents[0]).strip().find('.') + 3]
                            price = float(ps)
                            if lowPrice == None or price < lowPrice:
                                lowPrice = price
                        
                        if fw.roundTrip and lowPrice is not None:
                            tdIn = soup.findAll("td", {"id": re.compile('matrix_cal_body_fare1_.*_in')})
                            for i in tdIn:
                                spp = i.find("span", {"class": "step2PricePoints "})
                                ps = str(spp.contents[0]).strip()[1:str(spp.contents[0]).strip().find('.') + 3]
                                price = float(ps)
                                if lowPriceRet == None or price < lowPriceRet:
                                    lowPriceRet = price
                            if lowPriceRet != None:
                                lowPrice = lowPrice + lowPriceRet
                                
                        volarisPrice = lowPrice
                        
                except urlfetch.DownloadError as err:
                    print 'Error Fetching URL: ' + url + ' --- Error Type: ' + str(type(err)) + ' --- Error Args: ' + str(err.args) + ' --- Error Message: ' + str(err)
                
                lowestPrice = None
                if volarisPrice is not None and aeroPrice is not None:
                    if float(volarisPrice) < float(aeroPrice):
                        lowestPrice = volarisPrice
                        fw.airline = "Volaris"
                    else:
                        lowestPrice = aeroPrice
                        fw.airline = "AeroMexico"
                elif volarisPrice is None and aeroPrice is not None:
                    lowestPrice = aeroPrice
                    fw.airline = "AeroMexico"
                elif volarisPrice is not None and aeroPrice is None:
                    lowestPrice = volarisPrice
                    fw.airline = "Volaris"
                    
                if lowestPrice is not None:
                    lowestPrice = float(lowestPrice)
                    curYear = datetime.now().year
                    fe = FlightEntry()
                    fe.dollars = True
                    fe.lowPrice = lowestPrice
                    fe.roundTrip = fw.roundTrip
                    fe.departCity = departCity
                    fe.returnCity = returnCity
                    fe.departDate = datetime(curYear, list(calendar.month_abbr).index(depMonth.capitalize()), int(depDay))
                    if fw.roundTrip:
                        fe.returnDate = datetime(curYear, list(calendar.month_abbr).index(retMonth.capitalize()), int(retDay))
                    fe.put()
                    newEntry = fw.lowPrice is None   
                    
                    email = fw.authorEmail
                    if fw.author is not None:
                        email = fw.author.email()
                    if not newEntry and email is not None:
                        if lowestPrice < fw.currentPrice:     
                            try:               
                                message = mail.EmailMessage()
                                message.sender = "kc@recroomrecords.com"
                                message.to = email
                                message.subject = 'Flight-Fight Update - Price Decrease'
                                message.body = 'Flight Fight Price Update:\n\nThe price of a monitored flight has gone DOWN!!\n\n Flight details:\n' + fw.departCity + ' to ' + fw.returnCity + ' on ' + str(fw.departDate) + '\nYour Target Price: ' + str(fw.targetPrice) + '\Previous Price: ' + str(fw.currentPrice) + '\nCurrent Price: ' + str(lowestPrice) + ' on ' + fw.airline
                                message.html = message.body + '<br><p>' + fw.getPurchaseLink() + 'This Flight<br><p>To deactivate this Flight Watch and no longer receive these notices, ' + fw.getRemoveLink('just click here.', 'http://flight-fight.appspot.com') + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.body = message.body + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.send()
                            finally:
                                SendPush().send(fw.author, 'update')                            
                                '''taskqueue.add(url='/sendPush', params={'accountName': fw.key(),'registrationId': fw.key(),'text': 'update'})'''
                        if lowestPrice > fw.currentPrice:
                            try:
                                message = mail.EmailMessage()
                                message.sender = "kc@recroomrecords.com"
                                message.to = email
                                message.subject = 'Flight-Fight Update - Price Increase'
                                message.body = 'Flight Fight Price Update:\n\nThe price of a monitored flight has gone UP!!\n\n Flight details:\n' + fw.departCity + ' to ' + fw.returnCity + ' on ' + str(fw.departDate) + '\nYour Target Price: ' + str(fw.targetPrice) + '\Previous Price: ' + str(fw.currentPrice) + '\nCurrent Price: ' + str(lowestPrice) + ' on ' + fw.airline
                                message.html = message.body + '<br><p>' + fw.getPurchaseLink() + 'This Flight<br><p>To deactivate this Flight Watch and no longer receive these notices, ' + fw.getRemoveLink('just click here.', 'http://flight-fight.appspot.com') + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.body = message.body + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.send()
                            finally:
                                SendPush().send(fw.author, 'update')
                            
                    if newEntry and fw.author is not None and fw.author.email() is not None:
                            try:
                                message = mail.EmailMessage()
                                message.sender = "kc@recroomrecords.com"
                                message.to = email
                                message.subject = 'Flight-Fight Update - New Flight Added'
                                message.body = 'Flight Fight Flight Tracking:\n\nYou are now monitoring a new flight on Volaris and AeroMexico!!\n\n Flight details:\n' + fw.departCity + ' to ' + fw.returnCity + ' on ' + str(fw.departDate) + '\nYour Target Price: ' + str(fw.targetPrice) + '\nCurrent Price: ' + str(lowestPrice) + ' on ' + fw.airline
                                message.html = message.body + '<br><p>' + fw.getPurchaseLink() + 'This Flight<br><p>To deactivate this Flight Watch and no longer receive these notices, ' + fw.getRemoveLink('just click here.', 'http://flight-fight.appspot.com') + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.body = message.body + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.send()
                            finally:
                                SendPush().send(fw.author, 'update')
                    
                    if newEntry or fw.currentPrice != lowestPrice:
                        if newEntry:
                            fw.currentPrice = lowestPrice
                            fw.dollars = curLocale == "en"
                            
                        if newEntry or lowestPrice < fw.lowPrice:
                            fw.lowPrice = lowestPrice
                                
                        if newEntry or lowestPrice > fw.highPrice:
                            fw.highPrice = lowestPrice 
                            
                        fw.previousPrice = fw.currentPrice
                        fw.currentPrice = lowestPrice
                        fw.dateModified = datetime.now()
                        fw.put();

class CronJob(webapp.RequestHandler):
    def get(self):    
        curLocale = 'en'        
        if self.request.get("locale"):
            curLocale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            curLocale = self.request.headers['Accept-Language'][0:2]   
                 
        fwu = FlightWatchUpdate()
        cuids = self.request.get('cuid')
        if cuids is not '':
            for fw in FlightWatch.all():
                for cuid in cuids.split(','):
                    if fw.authorEmail is not None:
                        if fw.authorEmail == cuid:
                            fwu.process(fw, curLocale)
                    if fw.author is not None:
                        if fw.author.email() == cuid:
                            fwu.process(fw, curLocale)
        else:
            for fw in FlightWatch.all():
                fwu.process(fw, curLocale)
            
class AddFlightWatch(webapp.RequestHandler):
    def post(self):
        curLocale = 'en'
        if self.request.get("locale"):
            curLocale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            curLocale = self.request.headers['Accept-Language'][0:2] 
            
        fwKey = self.request.get('fwKey')
        
        fw = FlightWatch.get(fwKey)
        if fw is not None:
            FlightWatchUpdate().process(fw, curLocale)

        
class Predictive(webapp.RequestHandler):
    def get(self):
        cities = City.all()
        
        returns = 0
        
        for dep in cities:
    
            direction = 'onewaytravel'
            departCity = dep.shortName
            depMonth = 'JUN'
            depDay = '30'
            returnCity = 'CUN'
            retMonth = 'JUN'
            retDay = '30'
            
            url = 'https://compras.volaris.mx/meridia?posid=C0WE&page=requestAirMessage_air&action=airRequest&realRequestAir=realRequestAir' + '&direction=' + direction + '&departCity=' + departCity + '&depMonth=' + depMonth + '&depDay=' + depDay + '&depTime=&returnCity=' + returnCity + '&ADT=1&CHD=0&INF=0&classService=CoachClass&actionType=nonFlex&flightType=1&language=en' + '&retMonth=' + retMonth + '&retDay=' + retDay + '&retTime='
            resultPage = urlfetch.fetch(url)
            if resultPage.status_code == 200:
                page = str(resultPage.content)
                soup = BeautifulSoup(page)
                span = soup.findAll("span", {"class": "step2PricePoints"})
                lowPrice = None
                for i in range(0, len(span)):
                    ps = str(span[i].contents[0]).strip()[1:]
                    price = float(ps)
                    if lowPrice == None or price < lowPrice:
                        lowPrice = price
                        
                print 'Lowest Price = ' + str(lowPrice)
                if lowPrice is not None:
                    curYear = datetime.now().year
                    fe = FlightEntry()
                    fe.lowPrice = float(lowPrice)
                    fe.roundTrip = not direction == 'onewaytravel'
                    fe.departCity = departCity
                    fe.returnCity = returnCity
                    fe.departDate = datetime(curYear, list(calendar.month_abbr).index(depMonth.capitalize()), int(depDay))
                    fe.returnDate = datetime(curYear, list(calendar.month_abbr).index(retMonth.capitalize()), int(retDay))
                    fe.put()
            else:
                print 'Error Fetching URL Data'
        print returns + ' returned values'
    
class Init(webapp.RequestHandler):
    def get(self):
        city = City()
        city.KeyName = "EZE"
        city.shortName = "EZE"
        city.longName = "Buenos Aires - Ezeiza"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CDG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DEN","DGO","FAT","GDL","HMO","HUX","IAH","JFK","LAP","LAS","LAX","LMM","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","ONT","ORD","PAZ","PHX","PVR","QRO","REX","SAL","SAP","SAT","SFO","SJD","SLP","SLW","SMF","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CNF"
        city.shortName = "CNF"
        city.longName = "Belo Horizonte"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "BSB"
        city.shortName = "BSB"
        city.longName = "Brasilia"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "CWB"
        city.shortName = "CWB"
        city.longName = "Curitiba"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "FLN"
        city.shortName = "FLN"
        city.longName = "Florianopolis "
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "FOR"
        city.shortName = "FOR"
        city.longName = "Fortaleza "
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "POA"
        city.shortName = "POA"
        city.longName = "Porto Alegre"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "REC"
        city.shortName = "REC"
        city.longName = "Recife"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "GIG"
        city.shortName = "GIG"
        city.longName = "Rio de Janeiro"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "GRU"
        city.shortName = "GRU"
        city.longName = "Sao Paulo - Guarulho"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DEN","DGO","FAT","GDL","HMO","HUX","IAH","JFK","LAP","LAS","LAX","LMM","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","ONT","ORD","PAZ","PHX","PVR","QRO","REX","SAL","SAP","SAT","SFO","SJD","SLP","SLW","SMF","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","YYZ","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "YUL"
        city.shortName = "YUL"
        city.longName = "Montreal - Trudeau"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "YYZ"
        city.shortName = "YYZ"
        city.longName = "Toronto - Pearson"
        city.associatedAirports = ["GDL","GRU","LIM","MEX","SCL","SJO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "CCP"
        city.shortName = "CCP"
        city.longName = "Concepcion"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "PUQ"
        city.shortName = "PUQ"
        city.longName = "Punta Arenas"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "SCL"
        city.shortName = "SCL"
        city.longName = "Santiago"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","CDG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DEN","DGO","FAT","GDL","HMO","HUX","IAH","JFK","LAP","LAS","LAX","LMM","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVR","QRO","REX","SAL","SAP","SAT","SFO","SJD","SLP","SLW","SMF","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "PVG"
        city.shortName = "PVG"
        city.longName = "Shanghai - Pudong"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CCS","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","GDL","GUA","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "AXM"
        city.shortName = "AXM"
        city.longName = "Armenia"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "BAQ"
        city.shortName = "BAQ"
        city.longName = "Barranquilla"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "BOG"
        city.shortName = "BOG"
        city.longName = "Bogota"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CDG","CEN","CJS","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","FAT","GDL","HMO","IAH","JFK","LAP","LAX","LMM","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVG","PVR","QRO","REX","SAT","SFO","SJD","SLP","SMF","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "BGA"
        city.shortName = "BGA"
        city.longName = "Bucaramanga"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "CLO"
        city.shortName = "CLO"
        city.longName = "Cali"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "CTG"
        city.shortName = "CTG"
        city.longName = "Cartagena"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "MDE"
        city.shortName = "MDE"
        city.longName = "Medellin"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "PEI"
        city.shortName = "PEI"
        city.longName = "Pereira"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "SJO"
        city.shortName = "SJO"
        city.longName = "San Jose - SJO"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","FAT","GDL","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LMM","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVG","PVR","QRO","REX","SAT","SFO","SJD","SLP","SLW","SMF","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","YYZ","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "PRG"
        city.shortName = "PRG"
        city.longName = "Praga"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "SAL"
        city.shortName = "SAL"
        city.longName = "San Salvador"
        city.associatedAirports = ["ACA","AGU","BJX","CDG","CJS","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LIM","MAM","MEX","MID","MLM","MTY","MZT","OAX","PVR","REX","SCL","SFO","SJD","SLP","TAM","TGZ","TRC","VER","VSA","ZCL"]
        city.put()

        city = City()
        city.KeyName = "LYS"
        city.shortName = "LYS"
        city.longName = "Lyon"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "MRS"
        city.shortName = "MRS"
        city.longName = "Marsella"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "NCE"
        city.shortName = "NCE"
        city.longName = "Niza"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "CDG"
        city.shortName = "CDG"
        city.longName = "Paris - Charles de Gaulle"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CDG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","IAH","JFK","LAP","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","OAX","ONT","ORD","PAZ","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "TLS"
        city.shortName = "TLS"
        city.longName = "Toulouse"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "FRA"
        city.shortName = "FRA"
        city.longName = "Frankfurt"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "GUA"
        city.shortName = "GUA"
        city.longName = "Guatemala"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","CCS","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","DTW","FAT","GDL","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","ORD","PAZ","PVG","PVR","QRO","REX","SFO","SLP","SLW","TAM","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "SAP"
        city.shortName = "SAP"
        city.longName = "San Pedro Sula"
        city.associatedAirports = ["ACA","AGU","BCN","BJX","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","HMO","IAD","IAH","JFK","LAP","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVR","REX","SAT","SCL","SFO","SJD","SLP","SMF","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MXP"
        city.shortName = "MXP"
        city.longName = "Milan - Malpensa"
        city.associatedAirports = ["CUN","GDL","MEX"]
        city.put()

        city = City()
        city.KeyName = "FCO"
        city.shortName = "FCO"
        city.longName = "Roma - Fiumicino"
        city.associatedAirports = ["ATL","CUN","GDL","MEX"]
        city.put()

        city = City()
        city.KeyName = "NRT"
        city.shortName = "NRT"
        city.longName = "Tokyo - Narita"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CCS","CEN","CJS","CME","CPE","CUL","CUN","CUU","DGO","GDL","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SCL","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "ACA"
        city.shortName = "ACA"
        city.longName = "Acapulco"
        city.associatedAirports = ["AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","JFK","LAP","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","YYZ","ZCL","ZLO"]
        city.put()

        city = City()
        city.KeyName = "AGU"
        city.shortName = "AGU"
        city.longName = "Aguascalientes"
        city.associatedAirports = ["ACA","ATL","BCN","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAH","IAD","JFK","LAP","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "SJD"
        city.shortName = "SJD"
        city.longName = "Cabo San Lucas"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BDL","BJX","BNA","BOG","BOS","BWI","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","CVG","DCA","DEN","DGO","DTW","EZE","FAT","GDL","GRU","HMO","IAD","IAH","JFK","LAS","LAX","LIM","LMM","MAD","MAM","MCI","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJO","SLC","SLP","SLW","STL","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CPE"
        city.shortName = "CPE"
        city.longName = "Campeche"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CME","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CUN"
        city.shortName = "CUN"
        city.longName = "Cancun"
        city.associatedAirports = ["ACA","AGU","ALB","AMS","ATL","BCN","BDL","BJX","BNA","BOG","BOS","BWI","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CUL","CUU","CVG","DCA","DEN","DGO","DTW","EZE","FAT","FCO","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LGA","LGW","LIM","LMM","LPA","MAD","MAM","MCI","MCO","MEM","MEX","MIA","MID","MLM","MSP","MSY","MTT","MTY","MXL","MXP","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHL","PHX","PTY","PVG","PVR","QRO","RDU","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SJU","SLC","SLP","SLW","STL","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","YYZ","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CTM"
        city.shortName = "CTM"
        city.longName = "Chetumal"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","BOG","CUU","GDL","HMO","JFK","LAP","LAS","LAX","MCO","MEX","MIA","MTT","MTY","MZT","NLD","OAX","ORD","PAZ","PHX","PVR","REX","SAT","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "CUU"
        city.shortName = "CUU"
        city.longName = "Chihuahua"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","BRO","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLC","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CME"
        city.shortName = "CME"
        city.longName = "Ciudad del Carmen"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CJS"
        city.shortName = "CJS"
        city.longName = "Ciudad Juarez"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","BRO","CCS","CDG","CEN","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PBC","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLC","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CEN"
        city.shortName = "CEN"
        city.longName = "Ciudad Obregon"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CJS","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "CLQ"
        city.shortName = "CLQ"
        city.longName = "Colima"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CCS","CDG","CME","CUN","CUU","EZE","FAT","GRU","GUA","HMO","HUX","IAH","JFK","LAS","LAX","LIM","MAD","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","ORD","PHX","PVG","REX","SAP","SAT","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "CZM"
        city.shortName = "CZM"
        city.longName = "Cozumel"
        city.associatedAirports = ["ATL"]
        city.put()

        city = City()
        city.KeyName = "CUL"
        city.shortName = "CUL"
        city.longName = "Culiacan"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","BRO","CCS","CDG","CEN","CJS","CME","CPE","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLC","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "DGO"
        city.shortName = "DGO"
        city.longName = "Durango"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DEN","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "GDL"
        city.shortName = "GDL"
        city.longName = "Guadalajara"
        city.associatedAirports = ["ACA","AGU","ALB","ATL","BCN","BDL","BJX","BNA","BOG","BOS","BRO","BWI","CCS","CDG","CEN","CJS","CME","CPE","CTM","CUL","CUN","CUU","CVG","DCA","DEN","DGO","DTW","EZE","FAT","FCO","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LGA","LIM","LMM","MAD","MAM","MCI","MCO","MEX","MIA","MID","MSY","MTT","MTY","MXL","MXP","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PBC","PHL","PHX","PTY","PVG","PVR","QRO","RDU","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SJU","SLC","SLP","SLW","SMF","STL","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","YYZ","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "HMO"
        city.shortName = "HMO"
        city.longName = "Hermosillo"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","BRO","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PBC","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLC","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "HUX"
        city.shortName = "HUX"
        city.longName = "Huatulco"
        city.associatedAirports = ["ACA","AGU","BCN","BJX","CEN","CJS","CLQ","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","IAH","LAP","LAS","LAX","LIM","LMM","MAM","MEX","MIA","MID","MLM","MTY","MXL","MZT","ORD","PAZ","PVR","REX","SCL","SFO","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "ZIH"
        city.shortName = "ZIH"
        city.longName = "Ixtapa Zihuatanejo"
        city.associatedAirports = ["AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZLO"]
        city.put()

        city = City()
        city.KeyName = "LAP"
        city.shortName = "LAP"
        city.longName = "La Paz"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJO","SLC","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "BJX"
        city.shortName = "BJX"
        city.longName = "Leon Bajio"
        city.associatedAirports = ["ACA","ATL","BCN","BOG","BRO","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "LMM"
        city.shortName = "LMM"
        city.longName = "Los Mochis"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "ZLO"
        city.shortName = "ZLO"
        city.longName = "Manzanillo"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","BOG","CCS","CDG","CJS","CME","CPE","CUL","CUN","CUU","DGO","DTW","EZE","FAT","GRU","GUA","HMO","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ORD","PAZ","PTY","PVG","QRO","REX","SAT","SCL","SFO","SJD","SJO","SLC","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MAM"
        city.shortName = "MAM"
        city.longName = "Matamoros"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DEN","EZE","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MCO","MEX","MIA","MID","MLM","MTT","MTY","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","SAL","SAP","SAT","SCL","SFO","SJD","SJO","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MZT"
        city.shortName = "MZT"
        city.longName = "Mazatlan"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "MID"
        city.shortName = "MID"
        city.longName = "Merida"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "MXL"
        city.shortName = "MXL"
        city.longName = "Mexicali"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CDG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","HUX","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MCO","MEX","MIA","MID","MLM","MTT","MTY","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PBC","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "MEX"
        city.shortName = "MEX"
        city.longName = "Mexico City"
        city.associatedAirports = ["ACA","ACE","AGP","AGU","ALB","AMS","ATL","AXM","BAQ","BCN","BDL","BGA","BJX","BNA","BOG","BOS","BRO","BSB","BWI","CCP","CCS","CDG","CEN","CIX","CJS","CLO","CLQ","CME","CNF","CPE","CTG","CTM","CUL","CUN","CUU","CUZ","CVG","CWB","DCA","DEN","DGO","DTW","EZE","FAT","FCO","FLN","FOR","FRA","GDL","GIG","GRU","GUA","HMO","HUX","IAD","IAH","ICN","JFK","JUL","LAP","LAS","LAX","LGA","LGW","LHR","LIM","LIS","LMM","LPA","LYS","MAD","MAM","MCI","MCO","MDE","MIA","MID","MLM","MRS","MSP","MSY","MTT","MTY","MXL","MXP","MZT","NCE","NLD","NRT","OAX","ONT","ORD","PAZ","PDX","PEI","PEM","PHL","PHX","PMI","POA","PRG","PTY","PUQ","PVG","PVR","QRO","RDU","REC","REX","RIC","ROC","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SJU","SLC","SLP","SLW","SMF","STL","TAM","TAP","TGZ","TIJ","TLS","TRC","VER","VGO","VLC","VSA","YUL","YYZ","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "MTT"
        city.shortName = "MTT"
        city.longName = "Minatitlan"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "MTY"
        city.shortName = "MTY"
        city.longName = "Monterrey"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","BRO","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","DTW","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PBC","PHX","PTY","PVG","PVR","QRO","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLC","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "MLM"
        city.shortName = "MLM"
        city.longName = "Morelia"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "NLD"
        city.shortName = "NLD"
        city.longName = "Nuevo Laredo"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "OAX"
        city.shortName = "OAX"
        city.longName = "Oaxaca"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "PAZ"
        city.shortName = "PAZ"
        city.longName = "Poza Rica"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "PBC"
        city.shortName = "PBC"
        city.longName = "Puebla"
        city.associatedAirports = ["BRO","CJS","GDL","HMO","LAS","MTY","MXL","VSA"]
        city.put()

        city = City()
        city.KeyName = "PVR"
        city.shortName = "PVR"
        city.longName = "Puerto Vallarta"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BDL","BJX","BOG","BWI","CCS","CDG","CEN","CJS","CME","CPE","CTM","CUL","CUN","CUU","CVG","DCA","DEN","DGO","DTW","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLC","SLP","SLW","STL","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "QRO"
        city.shortName = "QRO"
        city.longName = "Queretaro"
        city.associatedAirports = ["ACA","AGU","BCN","BOG","BRO","CCS","CDG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PVG","PVR","REX","SAT","SCL","SFO","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "REX"
        city.shortName = "REX"
        city.longName = "Reynosa"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MCO","MEX","MIA","MID","MLM","MTT","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "SLW"
        city.shortName = "SLW"
        city.longName = "Saltillo"
        city.associatedAirports = ["ACA","AGU","BCN","BJX","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAX","LIM","LMM","MCO","MEX","MIA","MID","MLM","MTT","MXL","MZT","NRT","OAX","ORD","PAZ","PVG","PVR","SAT","SCL","SFO","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","VER","VSA","YUL","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "SLP"
        city.shortName = "SLP"
        city.longName = "San Luis Potosi"
        city.associatedAirports = ["ACA","ATL","BCN","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "TAM"
        city.shortName = "TAM"
        city.longName = "Tampico"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","BRO","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "TAP"
        city.shortName = "TAP"
        city.longName = "Tapachula"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","HMO","HUX","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TGZ","TIJ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "TIJ"
        city.shortName = "TIJ"
        city.longName = "Tijuana"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","ICN","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TRC","VER","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "TRC"
        city.shortName = "TRC"
        city.longName = "Torreon"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLC","SLP","TAM","TAP","TGZ","TIJ","VER","VSA","YUL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "TGZ"
        city.shortName = "TGZ"
        city.longName = "Tuxtla Gutierrez"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TIJ","TRC","VER","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "VER"
        city.shortName = "VER"
        city.longName = "Veracruz"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","BRO","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VSA","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "VSA"
        city.shortName = "VSA"
        city.longName = "Villahermosa"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","BOG","CCS","CDG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DEN","DGO","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MAM","MCO","MEX","MIA","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PBC","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLP","SLW","TAM","TAP","TIJ","TRC","VER","YUL","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "ZCL"
        city.shortName = "ZCL"
        city.longName = "Zacatecas"
        city.associatedAirports = ["ACA","ATL","BCN","BJX","BOG","CDG","CJS","CLQ","CME","CPE","CTM","CCS","CUL","CUN","CUU","DEN","EZE","FAT","GDL","GRU","GUA","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LIM","LMM","MAD","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","NRT","OAX","ONT","ORD","PAZ","PHX","PTY","PVG","PVR","QRO","REX","SAL","SAP","SAT","SCL","SFO","SJD","SJO","SLW","TAM","TAP","TGZ","TIJ","VER","VSA","YUL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "AMS"
        city.shortName = "AMS"
        city.longName = "Amsterdam"
        city.associatedAirports = ["CUN","MEX"]
        city.put()

        city = City()
        city.KeyName = "PTY"
        city.shortName = "PTY"
        city.longName = "Panama"
        city.associatedAirports = ["ACA","AGU","ATL","BCN","BJX","CEN","CJS","CPE","CUL","CUN","CUU","DGO","FAT","GDL","HMO","IAD","IAH","JFK","LAP","LAS","LAX","LMM","MAM","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","ORD","PAZ","PVR","REX","SFO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "CIX"
        city.shortName = "CIX"
        city.longName = "Chiclayo"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "CUZ"
        city.shortName = "CUZ"
        city.longName = "Cuzco"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "JUL"
        city.shortName = "JUL"
        city.longName = "Juliaca"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "LIM"
        city.shortName = "LIM"
        city.longName = "Lima"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CDG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DEN","DGO","FAT","GDL","HMO","HUX","IAD","IAH","JFK","LAP","LAS","LAX","LMM","MAM","MCO","MEX","MIA","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","ONT","ORD","PAZ","PHX","PVR","QRO","REX","SAL","SAP","SAT","SFO","SJD","SLP","SLW","SMF","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","YUL","YYZ","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "PEM"
        city.shortName = "PEM"
        city.longName = "Puerto Maldonado"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "LIS"
        city.shortName = "LIS"
        city.longName = "Lisboa"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "SJU"
        city.shortName = "SJU"
        city.longName = "San Juan"
        city.associatedAirports = ["CUN","GDL","MEX"]
        city.put()

        city = City()
        city.KeyName = "ICN"
        city.shortName = "ICN"
        city.longName = "Seul - Incheon"
        city.associatedAirports = ["MEX","TIJ"]
        city.put()

        city = City()
        city.KeyName = "BCN"
        city.shortName = "BCN"
        city.longName = "Barcelona"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CEN","CJS","CME","CPE","CUL","CUN","CUU","DGO","GDL","GUA","HMO","HUX","LAP","LMM","MAM","MEX","MID","MLM","MSY","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAP","SJD","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "LPA"
        city.shortName = "LPA"
        city.longName = "Gran Canaria"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "ACE"
        city.shortName = "ACE"
        city.longName = "Lanzarote"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "MAD"
        city.shortName = "MAD"
        city.longName = "Madrid"
        city.associatedAirports = ["ACA","AGU","BJX","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","GDL","GUA","HMO","LAP","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SJD","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "AGP"
        city.shortName = "AGP"
        city.longName = "Malaga"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "PMI"
        city.shortName = "PMI"
        city.longName = "Palma de Mallorca"
        city.associatedAirports = ["ATL","MEX"]
        city.put()

        city = City()
        city.KeyName = "VLC"
        city.shortName = "VLC"
        city.longName = "Valencia"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "VGO"
        city.shortName = "VGO"
        city.longName = "Vigo"
        city.associatedAirports = ["ATL","MEX"]
        city.put()

        city = City()
        city.KeyName = "LGW"
        city.shortName = "LGW"
        city.longName = "London - Gatwick"
        city.associatedAirports = ["CUN","MEX"]
        city.put()

        city = City()
        city.KeyName = "LHR"
        city.shortName = "LHR"
        city.longName = "London - Heathrow"
        city.associatedAirports = ["MEX"]
        city.put()

        city = City()
        city.KeyName = "ALB"
        city.shortName = "ALB"
        city.longName = "Albany"
        city.associatedAirports = ["CUN","GDL","MEX","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "ATL"
        city.shortName = "ATL"
        city.longName = "Atlanta"
        city.associatedAirports = ["ACA","AGU","BCN","BJX","BOG","BOS","CCS","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","CZM","DGO","DTW","EZE","FCO","GDL","GRU","GUA","HMO","JFK","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","ORD","PAZ","PMI","PTY","PVG","PVR","REX","ROC","SCL","SJD","SJO","SLC","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VGO","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "BWI"
        city.shortName = "BWI"
        city.longName = "Baltimore"
        city.associatedAirports = ["CUN","GDL","MEX","PVR","SJD","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "BOS"
        city.shortName = "BOS"
        city.longName = "Boston"
        city.associatedAirports = ["ATL","CUN","GDL","MEX","SJD","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "BRO"
        city.shortName = "BRO"
        city.longName = "Brownsville"
        city.associatedAirports = ["BJX","CJS","CUL","CUU","GDL","HMO","MEX","MTY","PBC","QRO","TAM","VER","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "ORD"
        city.shortName = "ORD"
        city.longName = "Chicago - O'Hare"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","BOG","CCS","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","HUX","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAP","SCL","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "CVG"
        city.shortName = "CVG"
        city.longName = "Cincinnati"
        city.associatedAirports = ["CUN","GDL","MEX","PVR","SJD","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "DEN"
        city.shortName = "DEN"
        city.longName = "Denver"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "DTW"
        city.shortName = "DTW"
        city.longName = "Detroit - Metro"
        city.associatedAirports = ["ATL","CCS","CUN","GDL","GUA","MEX","MTY","PVR","SJD","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()
        
        city = City()
        city.KeyName = "FAT"
        city.shortName = "FAT"
        city.longName = "Fresno"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAP","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "BDL"
        city.shortName = "BDL"
        city.longName = "Hartford Springfield"
        city.associatedAirports = ["CUN","GDL","MEX","PVR","SJD""ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "IAH"
        city.shortName = "IAH"
        city.longName = "Houston - George Bush"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CCS","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","HUX","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAL","SAP","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MCI"
        city.shortName = "MCI"
        city.longName = "Kansas City"
        city.associatedAirports = ["CUN","GDL","MEX","SJD","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "LAS"
        city.shortName = "LAS"
        city.longName = "Las Vegas"
        city.associatedAirports = ["ACA","AGU","BJX","CCS","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","HUX","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PBC","PTY","PVR","QRO","REX","SAL","SCL","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "LAX"
        city.shortName = "LAX"
        city.longName = "Los Angeles"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CCS","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","HUX","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAL","SAP","SCL","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MEM"
        city.shortName = "MEM"
        city.longName = "Memphis"
        city.associatedAirports = ["CUN","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MIA"
        city.shortName = "MIA"
        city.longName = "Miami"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","HUX","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAP","SCL","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MSP"
        city.shortName = "MSP"
        city.longName = "Minneapolis - St. Paul"
        city.associatedAirports = ["MEX","CUN","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "JFK"
        city.shortName = "JFK"
        city.longName = "New York - John F Kennedy"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","BOG","CCS","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAL","SAP","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "LGA"
        city.shortName = "LGA"
        city.longName = "New York - La Guardia"
        city.associatedAirports = ["CUN","GDL","MEX"]
        city.put()

        city = City()
        city.KeyName = "MSY"
        city.shortName = "MSY"
        city.longName = "New Orleans"
        city.associatedAirports = ["ACA","AGU","BJX","CME","CPE","CUN","CUU","GDL","MEX","MID","MTY","MZT","OAX","PVR","SJD","TRC","VSA","ZIH"]
        city.put()

        city = City()
        city.KeyName = "ONT"
        city.shortName = "ONT"
        city.longName = "Ontario"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "MCO"
        city.shortName = "MCO"
        city.longName = "Orlando"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SCL","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "PHL"
        city.shortName = "PHL"
        city.longName = "Philadelphia"
        city.associatedAirports = ["CUN","GDL","MEX","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "PHX"
        city.shortName = "PHX"
        city.longName = "Phoenix"
        city.associatedAirports = ["ACA","AGU","BJX","BOG","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SCL","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "PDX"
        city.shortName = "PDX"
        city.longName = "Portland"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "STL"
        city.shortName = "STL"
        city.longName = "St. Louis"
        city.associatedAirports = ["CUN","GDL","MEX","PVR","SJD","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "DCA"
        city.shortName = "DCA"
        city.longName = "Washington - Ronald Reagan"
        city.associatedAirports = ["CUN","GDL","MEX","SJD"]
        city.put()

        city = City()
        city.KeyName = "IAD"
        city.shortName = "IAD"
        city.longName = "Washington - Dulles"
        city.associatedAirports = ["ACA","AGU","BJX","CEN","CJS","CME","CPE","CUL","CUN","CUU","GDL","GUA","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MZT","NLD","OAX","PTY","PVR","QRO","REX","SAL","SAP","SJD","SJO","SLP","SLW","TAM","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "CCS"
        city.shortName = "CCS"
        city.longName = "Caracas"
        city.associatedAirports = ["ACA","AGU","ATL","BJX","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","DTW","GDL","GUA","HMO","IAH","JFK","LAP","LAS","LAX","LMM","MAM","MEX","MID","MLM","MTT","MTY","MZT","NLD","NRT","OAX","ORD","PAZ","PVG","PVR","QRO","REX","SAT","SLC","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "BNA"
        city.shortName = "BNA"
        city.longName = "Nashville"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH","CUN","GDL","MEX","SJD"]
        city.put()

        city = City()
        city.KeyName = "MSY"
        city.shortName = "MSY"
        city.longName = "New Orleans"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()        

        city = City()
        city.KeyName = "RDU"
        city.shortName = "RDU"
        city.longName = "Raleigh - Durham"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH","CUN","GDL","MEX"]
        city.put()

        city = City()
        city.KeyName = "RIC"
        city.shortName = "RIC"
        city.longName = "Richmond"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH"]
        city.put()

        city = City()
        city.KeyName = "ROC"
        city.shortName = "ROC"
        city.longName = "Rochester"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH","ATL","MEX"]
        city.put()

        city = City()
        city.KeyName = "SAT"
        city.shortName = "SAT"
        city.longName = "San Antonio"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH","ACA","AGU","BJX","BOG","CCS","CEN","CJS","CLQ","CME","CPE","CTM","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SCL","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "SFO"
        city.shortName = "SFO"
        city.longName = "San Francisco"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH","ACA","AGU","BJX","BOG","CEN","CJS","CLQ","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","GUA","HMO","HUX","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PTY","PVR","QRO","REX","SAL","SAP","SJD","SJO","SLP","SLW","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH","ZLO"]
        city.put()

        city = City()
        city.KeyName = "SLC"
        city.shortName = "SLC"
        city.longName = "Salt Lake City"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH","ATL","CCS","CJS","CUL","CUN","CUU","GDL","HMO","LAP","MEX","MTY","PVR","SJD","TRC","ZLO"]
        city.put()

        city = City()
        city.KeyName = "SMF"
        city.shortName = "SMF"
        city.longName = "Sacramento"
        city.associatedAirports = ["ACA","EZE","CUN","GDL","GUA","HUX","MEX","MID","MZT","OAX","PVR","GRU","SJD","SJO","ZIH","ACA","AGU","AGU","BJX","BOG","CEN","CJS","CME","CPE","CUL","CUN","CUU","DGO","EZE","GDL","GRU","HMO","LAP","LIM","LMM","MAM","MEX","MID","MLM","MTT","MTY","MXL","MZT","NLD","OAX","PAZ","PVR","QRO","REX","SAP","SJD","SJO","SLP","TAM","TAP","TGZ","TIJ","TRC","VER","VSA","ZCL","ZIH"]
        city.put()

        city = City()
        city.KeyName = "UPN"
        city.shortName = "UPN"
        city.longName = "Uruapan"
        city.put()

        city = City()
        city.KeyName = "TLC"
        city.shortName = "TLC"
        city.longName = "Toluca"
        city.put()

        city = City()
        city.KeyName = "CVJ"
        city.shortName = "CVJ"
        city.longName = "Cuernavaca"
        city.put()

        city = City()
        city.KeyName = "MDW"
        city.shortName = "MDW"
        city.longName = "Chicago / Midway"
        city.put()
        
        city = City()
        city.KeyName = "SAN"
        city.shortName = "SAN"
        city.longName = "San Diego"
        city.put()
        
        city = City()
        city.KeyName = "OAK"
        city.shortName = "OAK"
        city.longName = "San Francisco - Oakland"
        city.put()        
        
        city = City()
        city.KeyName = "SJC"
        city.shortName = "SJC"
        city.longName = "San Jose - SJC"
        city.put()


class StartPage(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write('<html>')
        self.response.out.write('<head>')
        self.response.out.write('<title>')
        self.response.out.write('Push')
        self.response.out.write('</title>')
        self.response.out.write('</head>')
        self.response.out.write('<body>')
        self.response.out.write('<form action=\"/sender\" method=\"POST\">')
        self.response.out.write('<select name=\"accountName\">')
        self.response.out.write('<option value=\"-\">-</option>')
        items = db.GqlQuery("SELECT * FROM Registration")
        for r in items:
            self.response.out.write('<option value=\"' + r.accountName + '\">' + r.accountName + '</option>')            
        self.response.out.write('</select>')
        self.response.out.write('<br>')
        self.response.out.write('<input type=\"text\" name=\"text\" size=\"30\"/>')
        self.response.out.write('<br>')
        self.response.out.write('<input type=\"submit\" value=\"Send message\">')
        self.response.out.write('</form>')
        self.response.out.write('</body>')
        self.response.out.write('</html>')

class Sender(webapp.RequestHandler):
    def post(self):
        accountName = self.request.get("accountName")
        text = self.request.get("text")
        itemquery = db.GqlQuery("SELECT * FROM Registration WHERE accountName=:1",
                                accountName)
        items = itemquery.fetch(1)
        self.response.headers['Content-Type'] = 'text/html'
        self.response.set_status(200, "OK")
        self.response.out.write('<html>')
        self.response.out.write('<head>')
        self.response.out.write('<title>')
        self.response.out.write('Push')
        self.response.out.write('</title>')
        self.response.out.write('</head>')
        self.response.out.write('<body>')
        if len(items) > 0:
            registration = items[0]
            registrationId = registration.registrationId
            status = self.sendMessage(accountName, registrationId, text)
            self.response.out.write('<p>Message sent, status: ' + status + '</p>')
        else:
            self.response.out.write("<p>No registration for '" + accountName + "'</p>")
        self.response.out.write('<p><a href=\"/\">Back to start page</a></p>')
        self.response.out.write('</body>')
        self.response.out.write('</htnl>')
                    
    def sendMessage(self, accountName, registrationId, text):
        global collapse_key
        global server_account_name
        authToken = self.getAuthToken()
        if authToken == "":
            return "Cannot authenticate " + server_account_name 
        form_fields = {
            "registration_id": registrationId,
            "collapse_key": str(collapse_key),
            "data.message": text
        }
        logging.info("authToken: " + authToken)
        form_data = urllib.urlencode(form_fields)
        result = urlfetch.fetch(url="http://android.apis.google.com/c2dm/send",
                        payload=form_data,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded',
                                 'Authorization': 'GoogleLogin auth=' + authToken
                                })
        collapse_key = collapse_key + 1
        return result.content

    def getAuthToken(self):
        global server_account_name
        global server_account_password
        form_fields = {
            "accountType": "GOOGLE",
            "Email": server_account_name,
            "Passwd": server_account_password,
            "service": "ac2dm",
            "source": "mylifewithandroid-push-2.0"
        }
        form_data = urllib.urlencode(form_fields)
        result = urlfetch.fetch(url="http://www.google.com/accounts/ClientLogin",
                        payload=form_data,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'
                                })
        if result.status_code == 200:
            logging.info("Auth response: " + result.content)
            lines = result.content.split('\n')
            authToken = ""
            for line in lines:
                if line.startswith("Auth="):
                    authToken = line[5:len(line)]
            return authToken
        logging.error("error code: " + str(result.status_code) + "; error message: " + result.content)
        return ""

class TokenService(webapp.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.set_status(500, "Server error")
        self.response.out.write("GET not supported")

    def post(self):
        accountName = self.request.get("accountName")
        registrationId = self.request.get("registrationId")
        logging.info("TokenService, accountName: " + accountName + \
                        "; registrationId: " + registrationId)
        self.updateOrInsertRegistration(accountName, registrationId)
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.set_status(200, "Registration accepted")
        self.response.out.write("Registration accepted")

    def updateOrInsertRegistration(self, accountName, registrationId):
        itemquery = db.GqlQuery("SELECT * FROM Registration WHERE accountName=:1",
                                accountName)
        items = itemquery.fetch(1)
        if len(items) > 0:
            registration = items[0]
            if registrationId == "":  # unregistration
                registration.delete()
            else:
                registration.registrationId = registrationId
                registration.put()
        else:
            registration = Registration()
            registration.accountName = accountName
            registration.registrationId = registrationId
            registration.put()
            
            

class GetData(webapp.RequestHandler):
    def get(self):
        query = FlightWatch.all()                    
        result = '{\"FlightWatches\" :\n \t[ '
        cuids = self.request.get('cuid')
        if cuids is not None:
            for fw in query:
                for cuid in cuids.split(','):
                    if fw.authorEmail is not None:
                        if fw.authorEmail == cuid:
                            result = result + '\n\t\t' + utils.GqlEncoder().encode(fw) + ',\n'
                    if fw.author is not None:
                        if fw.author.email() == cuid:
                            result = result + '\n\t\t' + utils.GqlEncoder().encode(fw) + ',\n'   
                        
                        
            if result[result.__len__() - 2:] == ',\n':
                result = result[:-2]
            self.response.headers['Content-Type'] = "text/plain" # Alt. application/json
            self.response.out.write( result + '\n\t]\n}' )

class Login(webapp.RequestHandler):
    def get(self):
        if self.request.get('destination'):
            destination = self.request.get('destination')
        elif self.request.get('fwKey'):
            destination = '/overview?fwKey=' + self.request.get('fwKey')
        else:
            destination = '/overview'
        # template_values = {
        # }
        
        # path = os.path.join(os.path.dirname(__file__), 'login.html')
        self.response.out.write('Almost There! Please sign in at: ')
        for name, uri in providers.items():
            self.response.out.write('[<a href="%s">%s</a>]' % (
                users.create_login_url(dest_url=destination, federated_identity=uri), name))

class Remove(webapp.RequestHandler):
    def get(self):
        if self.request.get('fwKey'):
            key = self.request.get('fwKey')
            fw = FlightWatch.get(key)
            if fw is not None:
                fw.active = False
                fw.put()
                self.response.out.write('Successfully deactivated Flight Watch<br>You will no longer receive notifications for this flight.<br><p>Thank You!<br><br><p>Flight Fight Team')
            else:                
                self.response.out.write('Oops!  That Flight Watch could not be found.  Please reply to the email that directed you here and mention this error.<br><p>Thank You!<br><br><p>Flight Fight Team')
        else:                
            self.response.out.write('Oops!  That Flight Watch could not be found.  Please reply to the email that directed you here and mention this error.<br><p>Thank You!<br><br><p>Flight Fight Team')


class tV(webapp.RequestHandler):
    def get(self):        
        city = transCity()
        city.KeyName = "ACA"
        city.shortName = "ACA"
        city.longName = "Acapulco"
        city.associatedAirports = ["TIJ","SJD","MTY","LAP","CUL"]
        city.put()

        city = transCity()
        city.KeyName = "LAX"
        city.shortName = "LAX"
        city.longName = "Los Angeles"
        city.associatedAirports = ["MEX","CUN","GDL","AGU","MTY","SJD","HMO","LAP","CUL","PBC","LMM","CUU","UPN","CUU","ZCL","TLC","MLM"]
        city.put()

        city = transCity()
        city.KeyName = "TLC"
        city.shortName = "TLC"
        city.longName = "Toluca"
        city.associatedAirports = ["SJC","MDW","LAS","LAX","TIJ","MZT","GDL","CUN","SJD","TUS","TUL","TPA","STL","SNA","SMF","SLC","SFO","SEA","RNO","RDU","PHX","PHL","PDX","ORF","ONT","OMA","MHT","MCI","IND","GEG","ELP","DEN","CMH","BWI","BUR","BOI","BNA","ABQ"]
        city.put()

        city = transCity()
        city.KeyName = "AGU"
        city.shortName = "AGU"
        city.longName = "Aguascalientes"
        city.associatedAirports = ["LAX","TIJ","SJD","LAP","CUN","SAN","LAS","CUL","HMO"]
        city.put()

        city = transCity()
        city.KeyName = "CUN"
        city.shortName = "CUN"
        city.longName = "Cancun"
        city.associatedAirports = ["CUU","SJC","OAK","MXL","LAX","LAP","HMO","FAT","CUL","PBC","MEX","GDL","MTY","BJX","AGU","TLC","MDW","LAS","MCO","TIJ","SJD","PVR"]
        city.put()

        city = transCity()
        city.KeyName = "MEX"
        city.shortName = "MEX"
        city.longName = "Mexico City"
        city.associatedAirports = ["TIJ","SJD","MXL","SJC","MDW","LAX","LAS","LAP","FAT","CUL","PVR","MTY","GDL","HMO","SAN","CUU","CUN","TUS","TUL","TPA","STL","SNA","SMF","SLC","SFO","SEA","SDF","RNO","RDU","PVD","PIT","PHX","PHL","PDX","ORF","ONT","OMA","OKC","MSY","MSP","MHT","MCI","LGA","ISP","IND","IAD","GEG","EWR","ELP","DTW","DEN","CMH","CLE","BWI","BUR","BUF","BOS","BOI","BNA","BDL","AUS","ALB","ABQ","MCO","OAK","LMM"]
        city.put()

        city = transCity()
        city.KeyName = "CUU"
        city.shortName = "CUU"
        city.longName = "Chihuahua"
        city.associatedAirports = ["GDL","CUN","MEX","CUL","MDW","LAP","HMO","MCO","SJD","PVR","TIJ"]
        city.put()

        city = transCity()
        city.KeyName = "CVJ"
        city.shortName = "CVJ"
        city.longName = "Cuernavaca"
        city.associatedAirports = ["TIJ","LAP","LAP","HMO","CUL"]
        city.put()

        city = transCity()
        city.KeyName = "CUL"
        city.shortName = "CUL"
        city.longName = "Culiacan"
        city.associatedAirports = ["SJD","LAP","TLC","CUN","TIJ","MEX","GDL","HMO","CUU","MXL","MDW","LAS","ZCL","UPN","OAX","SJC","PVR","OAK","LAX","MTY","MLM","BJX","MCO","AGU","ACA","CVJ"]
        city.put()

        city = transCity()
        city.KeyName = "GDL"
        city.shortName = "GDL"
        city.longName = "Guadalajara"
        city.associatedAirports = ["CUU","FAT","TLC","TIJ","MXL","MEX","LAP","HMO","MTY","LMM","PBC","MKE","MHT","MCI","MAF","LIT","LGA","LBB","JAX","ISP","IND","IAD","HOU","GEG","FLL","EWR","ELP","ECP","DTW","DEN","DAL","CMH","CLE","BWI","BUR","BUF","BOS","BOI","BNA","BHM","BDL","AUS","AMA","ALB","ABQ","CUN","TUS","TUL","TPA","CUL","MCO","STL","SNA","SMF","SLC","SFO","SJC","SAN","OAK","MDW","LAX","LAS","SEA","SDF","SJD","SAT","RNO","RDU","PVD","PIT","PHX","PHL","PDX","ORF","ONT","OMA","OKC","MSY","MSP"]
        city.put()

        city = transCity()
        city.KeyName = "HMO"
        city.shortName = "HMO"
        city.longName = "Hermosillo"
        city.associatedAirports = ["TLC","CUN","TIJ","MEX","PBC","CUL","MDW","FAT","SJD","MZT","CUU","OAK","OAX","LAX","LAS","ZCL","UPN","GDL","PVR","LAP","MTY","MLM","LMM","BJX","AGU"]
        city.put()

        city = transCity()
        city.KeyName = "LAP"
        city.shortName = "LAP"
        city.longName = "La Paz"
        city.associatedAirports = ["MEX","CUL","TLC","MXL","CUN","PVR","AGU","OAK","MDW","UPN","OAX","MTY","CVJ","CUU","SJC","TIJ","LAS","LAX","MLM","CVJ","MZT","HMO","GDL","BJX","CLQ","ACA"]
        city.put()

        city = transCity()
        city.KeyName = "BJX"
        city.shortName = "BJX"
        city.longName = "Leon"
        city.associatedAirports = ["TIJ","SJD","CUN","MTY","LAP","CUL","MDW","LMM","HMO"]
        city.put()

        city = transCity()
        city.KeyName = "SJD"
        city.shortName = "SJD"
        city.longName = "Los Cabos"
        city.associatedAirports = ["CUL","AGU","OAK","UPN","OAX","MTY","MLM","MEX","HMO","BJX","ACA","PBC","PVR","MDW","ZCL","MXL","TIJ","TLC","PBC","SAN","LAX","CVJ","SJC","SAN","LAX","GDL","CUU","CUN","LAS","FAT"]
        city.put()

        city = transCity()
        city.KeyName = "MZT"
        city.shortName = "MZT"
        city.longName = "Mazatlan"
        city.associatedAirports = ["TIJ","UPN","TLC","MTY","OAX","CVJ"]
        city.put()

        city = transCity()
        city.KeyName = "MXL"
        city.shortName = "MXL"
        city.longName = "Mexicali"
        city.associatedAirports = ["TLC","LAP","CUN","MDW","CUL","MTY","SJD","GDL","MEX","LMM","PVR"]
        city.put()

        city = transCity()
        city.KeyName = "LAS"
        city.shortName = "LAS"
        city.longName = "Las Vegas"
        city.associatedAirports = ["TLC","MEX","GDL","CUL","PBC","MTY","LAP","HMO","CUN","LMM","MLM","CUU","PVR","SJD"]
        city.put()

        city = transCity()
        city.KeyName = "SAN"
        city.shortName = "SAN"
        city.longName = "San Diego"
        city.associatedAirports = ["MEX","GDL","CUL","MTY","CUN","TLC","LAP","HMO","CUU","PVR","LMM"]
        city.put()

        city = transCity()
        city.KeyName = "MDW"
        city.shortName = "MDW"
        city.longName = "Chicago / Midway"
        city.associatedAirports = ["TLC","MEX","GDL","MXL","LAP","HMO","CUL","TIJ","ZCL","MLM","CUN","PVR","LMM","CUU","BJX"]
        city.put()

        city = transCity()
        city.KeyName = "LMM"
        city.shortName = "LMM"
        city.longName = "Los Mochis"
        city.associatedAirports = ["TIJ","UPN","TLC","OAX","MTY","GDL","SJD","LAS","LAX","FAT","MLM","ACA","CUN","MEX","HMO","BJX"]
        city.put()

        city = transCity()
        city.KeyName = "MTY"
        city.shortName = "MTY"
        city.longName = "Monterrey"
        city.associatedAirports = ["TIJ","LAX","GDL","CUN","SJD","MZT","MLM","MEX","LMM","LAP","MDW","MXL","LAS","UPN","PVR","CUL","BJX","ACA","OAX","CVJ","CLQ","HMO","SJC"]
        city.put()

        city = transCity()
        city.KeyName = "OAX"
        city.shortName = "OAX"
        city.longName = "Oaxaca"
        city.associatedAirports = ["TIJ","SJD","LMM","LAP","CUL","HMO","MZT","MTY","GDL","AGU"]
        city.put()

        city = transCity()
        city.KeyName = "PBC"
        city.shortName = "PBC"
        city.longName = "Puebla"
        city.associatedAirports = ["TIJ","HMO","GDL","SJD","LAS","CUN","OAK","LAX","FAT","SJD","MXL","MTY","CUL","MDW"]
        city.put()

        city = transCity()
        city.KeyName = "PVR"
        city.shortName = "PVR"
        city.longName = "Puerto Vallarta"
        city.associatedAirports = ["TIJ","LAP","MEX","SJD","CUL","MTY","HMO","CVJ","SAN","OAK","MDW","LAS","MXL","CUU","CUN"]
        city.put()

        city = transCity()
        city.KeyName = "OAK"
        city.shortName = "OAK"
        city.longName = "San Francisco / Oakland"
        city.associatedAirports = ["TLC","MEX","CUN","SJD","LAP","PBC","GDL","CUL","LMM","PVR","MLM"]
        city.put()

        city = transCity()
        city.KeyName = "SJC"
        city.shortName = "SJC"
        city.longName = "San Jose California"
        city.associatedAirports = ["TLC","MEX","CUN","GDL","MLM"]
        city.put()

        city = transCity()
        city.KeyName = "TIJ"
        city.shortName = "TIJ"
        city.longName = "Tijuana"
        city.associatedAirports = ["ZCL","UPN","TLC","SJD","PVR","PBC","OAX","MZT","MTY","MLM","MEX","LMM","HMO","GDL","CLQ","MDW","LAP","CVJ","CUL","BJX","MCO","AGU","ACA","CUN","CUU"]
        city.put()

        city = transCity()
        city.KeyName = "UPN"
        city.shortName = "UPN"
        city.longName = "Uruapan"
        city.associatedAirports = ["TIJ","SJD","MZT","LAP","CUL","MTY","HMO","LAX"]
        city.put()

        city = transCity()
        city.KeyName = "ZCL"
        city.shortName = "ZCL"
        city.longName = "Zacatecas"
        city.associatedAirports = ["LAX","TIJ","CUL","MDW","LAP","SJD","HMO"]
        city.put()

        city = transCity()
        city.KeyName = "MCO"
        city.shortName = "MCO"
        city.longName = "Orlando"
        city.associatedAirports = ["TIJ","GDL","CUU","CUL","CUN","MEX"]
        city.put()

        city = transCity()
        city.KeyName = "MLM"
        city.shortName = "MLM"
        city.longName = "Morelia"
        city.associatedAirports = ["TIJ","LAX","SJD","MTY","MDW","LAP","SFO","PHX","OAK","LAS","DEN","LMM","HMO","CUL","TUS","SMF","SLC","SJC"]
        city.put()

        city = transCity()
        city.KeyName = "FAT"
        city.shortName = "FAT"
        city.longName = "Fresno"
        city.associatedAirports = ["GDL","TLC","MEX","CUN","HMO","LAP","PBC","LMM","CUU","SJD"]
        city.put()

        city = transCity()
        city.KeyName = "CLQ"
        city.shortName = "CLQ"
        city.longName = "Colima"
        city.associatedAirports = ["TIJ","LAP"]
        city.put()

        
        for transcity in transCity.all():
            for mainCity in transcity.associatedAirports:
                nomatch = True
                q = City.all()
                q.filter('shortName =', mainCity)
                for rootCity in q:
                    nomatch = False
                    if rootCity is None:
                        print 'error'
                    else:
                        rootCity.associatedAirports.append(transcity.shortName)
                        rootCity.put()
                
                if nomatch:
                    print '\n --' + mainCity
                

application = webapp.WSGIApplication([
  ('/', Home),
  ('/cron', CronJob),
  ('/cron/init', Init),
  ('/newflightwatch', AddFlightWatch),
  ('/insertfromandroid', InsertFromAndroid),
  ('/push', StartPage),
  ('/sender', Sender),
  ('/token', TokenService),
  ('/overview', Overview),
  ('/getdata', GetData),
  ('/about', About),
  ('/feedback', Feedback),
  ('/aero', Aero),
  ('/southwest', Southwest),
  ('/remove', Remove),
  ('/_ah/login_required', Login),
  ('/login', Login),
  ('/transVolaris', tV)
], debug=True)


def main():
    global collapse_key
    collapse_key = 1
    global server_account_name
    server_account_name = "kc@recroomrecords.com"
    global server_account_password
    server_account_password = "Tere4859"
    run_wsgi_app(application)


if __name__ == '__main__':
    main()
