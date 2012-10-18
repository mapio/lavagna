from cgi import escape 
from uuid import uuid4 
from datetime import datetime

from flask import Flask, render_template, request, Response, abort
from jinja2.exceptions import TemplateNotFound

from redis import StrictRedis

app = Flask( __name__ )
red = StrictRedis( unix_socket_path = './data/redis.sock' )

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
	red.publish( 'map', 'question@{0}@{1}'.format( student, location ) )
	red.publish( 'questions', u'<fieldset><legend>{0} {1}@{2}</legend>{3}</fieldset>'.format( now(), student, location, message ) )
	return ''

@app.route( '/stream/<channel>' )
def stream( channel ):
	def event_stream():
		if channel == 'map':
			for info in red.smembers( 'map' ):
				yield 'data: token@{0}\n\n'.format( info )
		pubsub = red.pubsub()
		pubsub.subscribe( channel )
		for message in pubsub.listen():
			if message[ 'type' ] != 'message': continue
			for line in message[ 'data' ].split( '\n' ):
				yield 'data: {0}\n'.format( line )
			yield '\n'
	return Response( event_stream(), mimetype = 'text/event-stream' )

@app.route( '/s/<token>' )
def student( token ):
	student, location = identify( token )
	if not student: abort( 404 )
	return render_template( 'student.html', token = token, student = student, location = location )

@app.route( '/get_token', methods = [ 'POST' ] )
def get_token():
	student, location = request.form[ 'student' ], request.form[ 'location' ]
	info = '{0}@{1}'.format( student, location )
	token = red.get( 'invtoken:{0}'.format( info ) )
	if not token:
		token = uuid4().hex
		red.sadd( 'map', info )
		red.publish( 'map', 'token@{0}'.format( info ) )
		red.set( 'invtoken:{0}'.format( info ), token )
		red.set( 'token:{0}'.format( token ), info )
	return Response( token, mimetype = 'text/plain' )

@app.route( '/t' )
def teacher():
	return render_template( 'teacher.html' )

@app.route( '/map/<room>' )
def map( room ):
	try:
		ret = render_template( 'maps/{0}.html'.format( room ) )
	except TemplateNotFound:
		abort( 404 )
	return ret

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
