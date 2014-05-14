import httplib
import mimetypes
import urlparse
import urllib

server_addr = "localhost:8081"

def post_multipart(host, selector, fields, files):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    content_type, body = encode_multipart_formdata(fields, files)
    h = httplib.HTTPConnection(host)
    headers = {
        'User-Agent': 'INSERT USERAGENTNAME',
        'Content-Type': content_type
        }
    h.request('POST', selector, body, headers)
    res = h.getresponse()
    return res

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def get_upload_url(client_id):
	fields = []
	fields.append(('client_id', client_id))
	response = post_multipart("localhost:8081", "/getuploadurl", fields, [])
	upload_url = response.read()
	return upload_url

def upload_message(sender_id, upload_url, filename, receiver):
	o = urlparse.urlparse(upload_url)
	fields = []
	fields.append(('client_id', sender_id))
	fields.append(('receiver', receiver))
	files = []
	f = open(filename)
	files.append(('file', filename, f.read()))
	r2 = post_multipart(o.netloc, o.path, fields, files)
	if (r2.status != 302):
		print "expected redirect (302) status after upload, got %d" % r2.status
#	keyurl = r2.getheader("Location")
#	o = urlparse.urlparse(keyurl)
#	conn.request("GET", o.path)
#	r3 = conn.getresponse()
#	download_url = str(urllib.unquote(r3.read()))
#	return download_url
	
def download_message(download_url):
	o = urlparse.urlparse(download_url)
	conn = httplib.HTTPConnection(o.netloc)
	conn.request("GET", o.path)
	resp = conn.getresponse()
	data = resp.read()
	return data

def register(phone_num, platform):
	fields = []
	fields.append(('phone_num', phone_num))
	fields.append(('platform', platform))
	response = post_multipart(server_addr, "/registerclient", fields, [])
	client_id = response.read()
	return client_id

def get_message_info(receiver_id):
	fields = []
	fields.append(('client_id', receiver_id))
	response = post_multipart(server_addr, "/getmessageinfo", fields, [])
	return (sender_phone_num, download_url)
	
def main():
	#httplib.HTTPConnection.debuglevel = 1

	# register sender and receiver
	sender_id = register('111-222-3333', 'android')
	print "sender ID:    " + sender_id
	receiver_id = register('444-555-6666', 'ios')
	print "receiver ID:    " + receiver_id

	# sender activities
	upload_url = get_upload_url(sender_id)
	print "upload URL:   " + upload_url
	filename = 'upload.me'
	upload_message(sender_id, upload_url, filename, '444-555-6666')
	print "uploaded file:" + filename
	return

	# receiver activities
	sender_phone_num, download_url = get_message_info(reciever_id)
	print "download URL: " + download_url
	print "sender phone number: " + sender_phone_num

	msg_data = download_message(download_url)
	o = urlparse.urlparse(download_url)
	filename = o.path.rsplit('/', 1)[1]
	f = open(filename, 'w')
	f.write(msg_data)
	print "saved file:   " + filename

if __name__ == '__main__':
	main()

### Registration ###
# client:
#   - send registration message to server (post /registerclient):
#      - phone number
#      - notification method
# server:
#   - create client record
#   - return client id
# client:
#   - remember client id
#
### Push Voice Message ###
# sender:
#   - get upload URL from server (post /getuploadurl)
#      - client id
# server:
#   - request upload URL from blob store
#   - return URL to caller
# sender:
#   - record message
#   - send data to server (post to upload url):
#      - client id
#      - message data
#      - recipient phone number
#      - sender phone number
# server:
#   - saves message data
#   - create message record
#      - blob_key
#      - sender id
#      - receiver id
#      - sent timestamp
#      - notification timestamp
#      - retrieved timestamp
#   - send notification to recipient
# receiver:
#   - receives notification
#   - requests message info from server (post /getmessageinfo):
#      - sender phone number
#      - download url
#   - downloads message data
#   - plays message
