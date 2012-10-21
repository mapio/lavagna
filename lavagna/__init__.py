from cgi import escape 
from json import dumps
from uuid import uuid4 
from datetime import datetime

from flask import Flask, render_template, request, Response, abort, session, redirect, url_for
from jinja2.exceptions import TemplateNotFound

from db import seat, studentat, question, answer, messages

app = Flask( __name__ )
app.secret_key = '899BFF36-68AF-47B8-A1F0-A764A96A90CF'	# should be in a conf file!
app.config[ 'SESSION_COOKIE_HTTPONLY' ] = False

@app.route( '/post/answer', methods = [ 'POST' ] )
def post_answer():
	f = request.form
	if not 'answer' in f: abort( 500 )
	if not 'kind' in f: abort( 500 )
	if not 'destination' in f: abort( 500 )
	answer( f[ 'answer' ], f[ 'kind' ], f[ 'destination' ] )
	return ''

@app.route( '/stream/<channel>' )
def stream( channel ):
	def event_stream():
		for data in messages( channel ):
			for line in data.split( '\n' ):
				yield 'data: {0}\n'.format( line )
			yield '\n'
	return Response( event_stream(), mimetype = 'text/event-stream' )

@app.route( '/post/question', methods = [ 'POST' ] )
def post_question():
	if 'location' in request.form: # this happens when the teacher deletes questions
		location = request.form[ 'location' ]
	elif 'location' in session: 
		location = session[ 'location' ]
	else: abort( 404 )
	if not 'question' in request.form: abort( 500 )
	question( request.form[ 'question' ], location )
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

@app.route( '/t/<rooms>' )
def teacher( rooms ):
	try:
		t = [ render_template( 'maps/{0}.html'.format( _ ) ) for _ in rooms.split( '+' ) ]
	except TemplateNotFound:
		abort( 404 )
	return render_template( 'teacher.html', rooms = ' '.join( t ) )

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
