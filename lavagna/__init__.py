from cgi import escape 
from ConfigParser import RawConfigParser
from functools import wraps
from json import dumps

from flask import Flask, render_template, request, Response, abort, session, redirect, url_for
from jinja2.exceptions import TemplateNotFound

import db

app = Flask( __name__ )
app.secret_key = db.secret( 'application' )

app.config[ 'SESSION_COOKIE_HTTPONLY' ] = False

# SSE endpoint

@app.route( '/stream/<stream>' )
# this must be secured using location and secret according to the stream
def stream( stream ):
	location = None
	if stream == 'teacher':
		if not 'secret' in session: abort( 500 )
	elif stream == 'student':
		if not 'location' in session: abort( 500 )
		else: location = session[ 'location' ]
	else: abort( 500 )
	def event_stream():
		for data in db.retrieve( stream, location ):
			for line in data.split( '\n' ):
				yield 'data: {0}\n'.format( line )
			yield '\n'
	return Response( event_stream(), mimetype = 'text/event-stream' )

# Student's endpoints

def student_required( view ):
	@wraps( view )
	def _view( *args, **kwargs ):
		if not 'location' in session: return redirect( url_for( 'login' ) )
		return view( *args, **kwargs )
	return _view

@app.route( '/login/<student>/<location>', methods = [ 'GET' ] )
@app.route( '/login', methods = [ 'GET', 'POST' ] )	
def login( student = None, location = None ):
	if request.method == 'POST':
		f = request.form
		if not 'location' in f: abort( 500 )
		if not 'student' in f: abort( 500 )
		if not 'token' in f: abort( 500 )
		location = f[ 'location' ]
		student = f[ 'student' ]
	if request.method == 'GET':
		if not ( student and location ): return render_template( 'login.html' )
	session[ 'location' ] = location
	db.login( student, location )
	return redirect( url_for( 'student' ) )

@app.route( '/' )
@student_required
def student():
	location = session[ 'location' ]
	student = db.logged( location )
	if not student:
		del session[ 'location' ]
		abort( 404 )
	return render_template( 'student.html', student = student, location = location )

@app.route( '/question', methods = [ 'POST' ] )
@student_required
def question():
	if not db.logged( session[ 'location' ] ): abort( 500 )
	if not 'question' in request.form: abort( 500 )
	db.question( request.form[ 'question' ], session[ 'location' ] )
	return ''

# Teacher's endpoints

def teacher_required( view ):
	@wraps( view )
	def _view( *args, **kwargs ):
		if not 'secret' in session or session[ 'secret' ] != db.secret( 'teacher' ): return redirect( url_for( 'tlogin' ) )
		return view( *args, **kwargs )
	return _view

@app.route( '/tlogin/<secret>', methods = [ 'GET' ] )
@app.route( '/tlogin', methods = [ 'GET', 'POST' ] )	
def tlogin( secret = None ):
	if request.method == 'POST':
		f = request.form
		if not 'secret' in f: abort( 500 )
		secret = f[ 'secret' ]
	if request.method == 'GET':
		if not secret: return render_template( 'tlogin.html' )
	if secret != db.secret( 'teacher' ): abort( 404 )
	session[ 'secret' ] = secret
	return redirect( url_for( 'teacher' ) )

@app.route( '/answer', methods = [ 'POST' ] )
@teacher_required
def answer():
	f = request.form
	if not 'answer' in f: abort( 500 )
	if not 'kind' in f: abort( 500 )
	if not 'destination' in f: abort( 500 )
	db.answer( f[ 'answer' ], f[ 'kind' ], f[ 'destination' ] )
	return ''

@app.route( '/clear_questions', methods = [ 'POST' ] )
@teacher_required
def clear_questions():
	if not 'location' in request.form: abort( 500 )
	if not db.logged( request.form[ 'location' ] ): abort( 500 )
	db.clear_questions( request.form[ 'location' ] )
	return ''

@app.route( '/logout/<location>')
@teacher_required
def logout( location ):
	db.logout( location )
	return 'OK'

@app.route( '/t/<rooms>' )
@app.route( '/t' )
@teacher_required
def teacher( rooms = 'guests' ):
	try:
		t = [ render_template( 'maps/{0}.html'.format( _ ) ) for _ in rooms.split( '+' ) ]
	except TemplateNotFound:
		abort( 404 )
	return render_template( 'teacher.html', rooms = ' '.join( t ) )

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
