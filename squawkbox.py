#!/usr/bin/env python
#

import os
import urllib
import logging
import datetime

from google.appengine.ext import blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

class Client(db.Model):
	phone_number = db.StringProperty(required=True)
	platform = db.StringProperty(required = True)
	
class Message(db.Model):
	blob = blobstore.BlobReferenceProperty(required=True)
	sender_id = db.StringProperty(required=True)
	receiver_id = db.StringProperty(required=True)
	sent = db.DateTimeProperty(required=True, auto_now_add=True)
	notification = db.DateTimeProperty()
	retrieved = db.DateTimeProperty()

# valid client ID?
def valid_client(client_id):
	return Client.get_by_id(int(client_id)) is not None
	
# TODO: valid platform?
def valid_platform(platform):
	return true

# TODO: valid phone number (i.e. is it in our list of registered clients)?
def valid_phone_number(number):
	return True
	
def get_client_from_phone(number):
	q = Client.gql("WHERE phone_number = :1", number)
	for client in q:
		logging.debug("Found client %d with phone number %s" % (client.key().id(), client.phone_number))
	if client:
		return client.key().id()
	else:
		return None

def get_phone_from_client(client_id):
	client = Client.get_by_id(client_id)
	if not client:
		return None
	else:
		return client.phone_number

# TODO: notify recipient of new message
def notify_recipient(client_id):
	return

class RegisterClientHandler(webapp.RequestHandler):
	def post(self):
		#   pull registration data from post data
		#   create client record in db
		#   return unique client id
		phone = self.request.get('phone_num')
		pf = self.request.get('platform')
		client = Client(phone_number = phone, platform = pf)
		client.put()
		self.response.out.write(str(client.key().id()))

# ask blobstore for upload URL
class GetUploadUrlHandler(webapp.RequestHandler):
	def post(self):
		client_id = self.request.get('client_id')
		logging.debug("requesting client_id is: %s" % client_id)
		if not valid_client(client_id):
			self.redirect('/badrequest')
		else:
			upload_url = blobstore.create_upload_url('/uploadmessage') # param is re-direct handler
			self.response.out.write(upload_url)

# upload request is re-directed to this handler after blob is uploaded to blobstore provided URL
# TODO: parse other form data (e.g. 'from', 'to')
#       create message record in db   
class UploadMessageHandler(blobstore_handlers.BlobstoreUploadHandler):
	def post(self):
		client_id = self.request.get('client_id')
		receiver_phone_number = self.request.get('receiver')
		upload_files = self.get_uploads('file')
		receiver_id = get_client_from_phone(receiver_phone_number)
		if len(upload_files) is 0 or not client_id or not valid_client(client_id) or not receiver_id:
			self.redirect('/badrequest')
		else:
			blob_info = upload_files[0]
			msg = Message(blob = blob_info.key(), sender_id = client_id, receiver_id = str(receiver_id))
			msg.put()
			notify_recipient(receiver_id)
			self.response.set_status(302)	# blobstore handler expects us to re-direct, it is ignored by the client

class GetDownloadUrlHandler(webapp.RequestHandler):
	def get(self, blob_key):
		url = "http://%s:%s/serve/%s" % (self.request.environ['SERVER_NAME'], self.request.environ['SERVER_PORT'], blob_key)
		self.response.out.write(url)

# get message info for requesting client
class GetMessageInfoHandler(webapp.RequestHandler):
	def post(self):
		client_id = self.request.get('client_id')
		logging.debug("requesting client_id is: %s" % client_id)
		if not valid_client(client_id):
			self.redirect('/badrequest')
		else:
			# find message for client
			q = Message.gql("where receiver_id = :1", client_id)
			for message in q:
				logging.debug("Found message %d" % message.key().id())
			if message:
				download_url = "http://%s:%s/serve/%s" % (self.request.environ['SERVER_NAME'], self.request.environ['SERVER_PORT'], message.blob.key().id())
				senders_num  = get_phone_from_client(message.sender_id)
				message.retrieved = datetime.datetime.now()
				message.put()
				self.response.out.write("%s,%s" % (senders_num, download_url))
			else:
				self.redirect('/badrequest')

#class ServeBlobKeyHandler(webapp.RequestHandler):
#	def get(self, resource):
#		self.response.out.write(resource) # resource is blob key

class BadRequestHandler(webapp.RequestHandler):
	def get(self):
		self.error(400) #bad request

#class MainHandler(webapp.RequestHandler):
#    def get(self):
#        upload_url = blobstore.create_upload_url('/upload')
#        self.response.out.write('<html><body>')
#        self.response.out.write('<form action="%s" method="POST" enctype="multipart/form-data">' % upload_url)
#        self.response.out.write("""Upload File: <input type="file" name="file"><br> <input type="submit"
#            name="submit" value="Submit"> </form>%s</body></html>""" % upload_url)

#class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
#    def post(self):
#        upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
#        blob_info = upload_files[0]
#        self.redirect('/serve/%s' % blob_info.key())

# send the blob to the client
class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)

def main():
    application = webapp.WSGIApplication(
          [
           ('/registerclient', RegisterClientHandler),
           ('/getuploadurl?', GetUploadUrlHandler),
           ('/uploadmessage', UploadMessageHandler),
           ('/getmessageinfo', GetMessageInfoHandler),
           ('/getdownloadurl/([^/]+)?', GetDownloadUrlHandler),
           ('/serve/([^/]+)?', ServeHandler),
           ('/badrequest', BadRequestHandler),
           #('/serveblobkey/([^/]+)?', ServeBlobKeyHandler),
           #('/upload', UploadHandler),
           #('/', MainHandler),
          ], debug=True)
    run_wsgi_app(application)

if __name__ == '__main__':
  main()