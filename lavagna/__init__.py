from cgi import escape 
from json import dumps
from uuid import uuid4 
from datetime import datetime

from flask import Flask, render_template, request, Response, abort, session, redirect, url_for
from jinja2.exceptions import TemplateNotFound

import db

app = Flask( __name__ )
app.secret_key = '899BFF36-68AF-47B8-A1F0-A764A96A90CF'	# should be in a conf file!
app.config[ 'SESSION_COOKIE_HTTPONLY' ] = False

@app.route( '/stream/<stream>' )
def stream( stream ):
	def event_stream():
		for data in db.retrieve( stream ):
			for line in data.split( '\n' ):
				yield 'data: {0}\n'.format( line )
			yield '\n'
	return Response( event_stream(), mimetype = 'text/event-stream' )

@app.route( '/post/answer', methods = [ 'POST' ] )
def answer():
	f = request.form
	if not 'answer' in f: abort( 500 )
	if not 'kind' in f: abort( 500 )
	if not 'destination' in f: abort( 500 )
	db.answer( f[ 'answer' ], f[ 'kind' ], f[ 'destination' ] )
	return ''

@app.route( '/post/question', methods = [ 'POST' ] )
def question():
	if not 'location' in session: abort( 404 )
	if not db.logged( session[ 'location' ] ): abort( 500 )
	if not 'question' in request.form: abort( 500 )
	db.question( request.form[ 'question' ], session[ 'location' ] )
	return ''

@app.route( '/post/clear_questions', methods = [ 'POST' ] )
def clear_questions():
	if not 'location' in request.form: abort( 500 )
	if not db.logged( request.form[ 'location' ] ): abort( 500 )
	db.clear_questions( request.form[ 'location' ] )
	return ''

@app.route( '/post/logout', methods = [ 'POST' ] )
def logout():
	if not 'location' in request.form: abort( 500 )
	db.logout( request.form[ 'location' ] )
	return 'OK'

@app.route( '/login/<student>/<location>' )	
def login( student, location ):
	session[ 'location' ] = location
	db.login( student, location )
	return redirect( url_for( 'student' ) )

@app.route( '/' )
def student():
	if not 'location' in session: abort( 404 )
	location = session[ 'location' ]
	student = db.logged( location )
	if not student: abort( 404 )
	return render_template( 'student.html', student = student, location = location )

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
