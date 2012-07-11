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
   
    def getRemoveLink(self, label):
        return '<a href="' + self.request.host_url + '/remove?fwKey=' + str(self.key()) + '">' + label + '</a>';

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
                lowPriceRet = None
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
                                  
                    
class Home(webapp.RequestHandler):
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
            url_login = users.create_login_url(self.request.uri)
            if locale == 'en':
                url_loginLinktext = 'Login'
            else:
                url_loginLinktext = 'Entrar'
            #self.redirect(users.create_login_url(self.request.uri))
        
        message = self.request.get("message");
        if message == '':
            if locale == 'en':
                message = 'Just fill and submit this form to start tracking the best price.'
            else:
                message = 'Just fill and submit this form to start tracking the best price.'
                
        if locale == 'en':
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

        template_values = {
            'url_login': url_login,
            'url_loginLinktext': url_loginLinktext,
            'cities': City.all(),
            'locale': locale,
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
            url_login = users.create_login_url(self.request.uri)
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
        isError = False
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
            url_login = users.create_login_url(self.request.uri)
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
                    titleLabel = 'Flight Watch Overview for ' + user.nickname()
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
                    titleLabel = 'Flight Watch Overview for ' + user.nickname()
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
    def process(self, fw, locale):
        if fw.active:
            if fw.departDate < datetime.now():
                fw.active = False
            else:
                direction = 'onewaytravel'
                returnString = ''
                retMonth = None
                retDay = None
                if fw.roundTrip:
                    direction = 'returntravel'
                    retMonth = list(calendar.month_abbr)[fw.returnDate.month]
                    retDay = str(fw.returnDate.day)
                    returnString = '&retMonth=' + retMonth + '&retDay=' + retDay + '&retTime='
                departCity = fw.departCity
                returnCity = fw.returnCity
                depMonth = list(calendar.month_abbr)[fw.departDate.month]
                depDay = str(fw.departDate.day)
                
                aeroPrice = Aero().process(direction, departCity, returnCity, depMonth, depDay, 2012, retMonth, retDay, 2012)
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
                        lowestPRice = aeroPrice
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
                                message.html = message.body + '<br><p>' + fw.getPurchaseLink() + 'This Flight<br><p>To deactivate this Flight Watch and no longer receive these notices, ' + fw.getRemoveLink('just click here.') + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
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
                                message.html = message.body + '<br><p>' + fw.getPurchaseLink() + 'This Flight<br><p>To deactivate this Flight Watch and no longer receive these notices, ' + fw.getRemoveLink('just click here.') + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
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
                                message.html = message.body + '<br><p>' + fw.getPurchaseLink() + 'This Flight<br><p>To deactivate this Flight Watch and no longer receive these notices, ' + fw.getRemoveLink('just click here.') + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.body = message.body + '\n\n Thank You,\n\n\n\nFlight-Fight Team'
                                message.send()
                            finally:
                                SendPush().send(fw.author, 'update')
                    
                    if newEntry or fw.currentPrice != lowestPrice:
                        if newEntry:
                            fw.currentPrice = lowestPrice
                            fw.dollars = locale == "en"
                            
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
        locale = 'en'        
        if self.request.get("locale"):
            locale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            locale = self.request.headers['Accept-Language'][0:2]   
                 
        fwu = FlightWatchUpdate()
        cuids = self.request.get('cuid')
        if cuids is not '':
            for fw in FlightWatch.all():
                for cuid in cuids.split(','):
                    if fw.authorEmail is not None:
                        if fw.authorEmail == cuid:
                            fwu.process(fw, locale)
                    if fw.author is not None:
                        if fw.author.email() == cuid:
                            fwu.process(fw, locale)
        else:
            for fw in FlightWatch.all():
                fwu.process(fw, locale)
            
class AddFlightWatch(webapp.RequestHandler):
    def post(self):
        locale = 'en'
        if self.request.get("locale"):
            locale = self.request.get("locale")[0:2]
        elif 'Accept-Language' in self.request.headers:
            locale = self.request.headers['Accept-Language'][0:2] 
            
        fwKey = self.request.get('fwKey')
        
        fw = FlightWatch.get(fwKey)
        if fw is not None:
            FlightWatchUpdate().process(fw, locale)

        
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
  ('/remove', Remove),
  ('/_ah/login_required', Login),
  ('/login', Login)
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
