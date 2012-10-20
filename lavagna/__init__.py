from cgi import escape 
from json import dumps
from uuid import uuid4 
from datetime import datetime

from flask import Flask, render_template, request, Response, abort, session, redirect, url_for
from jinja2.exceptions import TemplateNotFound

from redis import StrictRedis

from db import seat, studentat, question, answer

app = Flask( __name__ )
app.secret_key = '899BFF36-68AF-47B8-A1F0-A764A96A90CF'	# should be in a conf file!
app.config[ 'SESSION_COOKIE_HTTPONLY' ] = False

red = StrictRedis( unix_socket_path = './data/redis.sock' )

def now():
	return datetime.now().replace( microsecond = 0 ).time().isoformat()

@app.route( '/post/answer', methods = [ 'POST' ] )
def post_answer():
	f = request.form
	if not 'message' in f: abort( 500 )
	if not 'kind' in f: abort( 500 )
	if not 'destination' in f: abort( 500 )
	answer( f[ 'message' ], f[ 'kind' ], f[ 'destination' ] )
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

@app.route( '/post/question', methods = [ 'POST' ] )
def post_question():
	if not 'location' in session: abort( 404 )
	if not 'message' in request.form: abort( 500 )
	question( request.form[ 'message' ], session[ 'location' ] )
	return ''

@app.route( '/' )
def student():
	if not 'location' in session: abort( 404 )
	location = session[ 'location' ]
	student = studentat( location )
	return render_template( 'student.html', student = student, location = location )

@app.route( '/seat/<student>/<location>' )
def set_session( student, location ):
	session[ 'location' ] = location
	seat( student, location )
	return redirect( url_for( 'student' ) )

@app.route( '/t' )
def teacher():
	return render_template( 'teacher.html' )

@app.route( '/map/<room>' )
def map( room ):
	try:
		ret = render_template( 'maps/{0}.html'.format( room ) )
	except TemplateNotFound:
		abort( 404 )
	return render_template( 'maps/base.html', maps = ret )

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
