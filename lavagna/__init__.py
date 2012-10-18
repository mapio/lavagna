from cgi import escape 
from uuid import uuid4 
from datetime import datetime

from flask import Flask, render_template, request, Response, abort

import redis

app = Flask( __name__ )
red = redis.StrictRedis( unix_socket_path = './data/redis.sock' )

def now():
	return datetime.now().replace( microsecond = 0).time().isoformat()
	
def identify( token ):
	info = red.get( 'token:{0}'.format( token ) )
	if info: return info.split( '@' )
	else: return None, None

@app.route( '/post/hint/<kind>', methods = [ 'POST' ] )
def post_hint( kind ):
	message = request.form[ 'message' ]
	if ( kind != 'html' ):
		message = escape( message )
	if ( kind == 'text' ):
		content = '<pre style="white-space: pre-wrap;">{0}</pre>'.format( message )
	elif ( kind == 'code' ):
		content = '<pre class="pp">{0}</pre>'.format( message )
	else:
		content = message
	red.publish( 'hints', u'<fieldset><legend>{0}</legend>{1}</fieldset>'.format( now(), content ) )
	return ''

@app.route( '/post/question/<token>', methods = [ 'POST' ] )
def post_question( token ):
	student, location = identify( token )
	message = request.form[ 'message' ]
	red.publish( 'questions', u'<fieldset><legend>{0}, {1} @ {2}</legend>{3}</fieldset>'.format( student, location, now(), message ) )
	return ''

@app.route( '/stream/<channel>' )
def stream( channel ):
	def event_stream():
		pubsub = red.pubsub()
		pubsub.subscribe( channel )
		for message in pubsub.listen():
			if message[ 'type' ] != 'message': continue
			for line in message[ 'data' ].split( '\n' ):
				yield 'data: {0}\n'.format( line )
			yield '\n\n'
	return Response( event_stream(), mimetype = 'text/event-stream' )

@app.route( '/s/<token>' )
def student( token ):
	student, location = identify( token )
	if not student or not location: abort( 404 )
	return render_template( 'student.html', token = token, student = student, location = location )

@app.route( '/get_token', methods = [ 'POST' ] )
def get_token():
	uid = request.form[ 'uid' ]
	loc = request.form[ 'loc' ]
	token = uuid4().hex
	red.set( 'token:{0}'.format( token ), '{0}@{1}'.format( uid, loc ) )
	return Response( token, mimetype = 'text/plain' )

@app.route( '/t' )
def teacher():
	return render_template( 'teacher.html')

@app.route( '/map' )
def map():
	return render_template( 'map.html' )

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
