# Copyright (C) 2012 Massimo Santini <massimo.santini@unimi.it>
#
# This file is part of Lavagna.
#
# Lavagna is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Lavagna is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lavagna.  If not, see <http://www.gnu.org/licenses/>.

from functools import wraps

from jinja2.exceptions import TemplateNotFound
from flask import Flask, render_template, request, Response, abort, session, redirect, url_for, g

import db

app = Flask( __name__ )
app.config.update(
	DEBUG = True,
	TESTING = True,
	SECRET_KEY = db.secret( 'application' ),
	SECRET_TEACHER = db.secret( 'teacher' ),
	SECRET_STUDENTS = db.secret( 'students' ),
	SESSION_COOKIE_HTTPONLY = False,
)

@app.before_request
def before_request():
	g.teacher = False
	g.location, g.student = None, None
	if 'location' in session:
		g.location, g.student = session[ 'location' ], db.logged( session[ 'location' ] )
		if not ( g.location and g.student ):
			del session[ 'location' ]
			g.location, g.student = None, None
	secret = None
	if 'secret' in session: secret = session[ 'secret' ]
	elif request.method == 'POST' and 'secret' in request.form: secret = request.form[ 'secret' ]
	elif request.json and 'secret' in request.json: secret = request.json[ 'secret' ]
	if secret: g.teacher = secret == app.config[ 'SECRET_TEACHER' ]

# SSE endpoint

@app.route( '/stream/<stream>' )
def stream( stream ):
	location = None
	if stream == 'teacher':
		if not g.teacher: abort( 403 )
	elif stream == 'student':
		if not g.student: abort( 403 )
		else: location = g.location
	elif stream == 'term':
		if not ( g.student or g.teacher ): abort( 403 )
	else: abort( 500 )
	def event_stream():
		for data in db.retrieve( stream, location ):
			for line in data.split( '\n' ):
				yield 'data: {0}\n'.format( line )
			yield '\n'
	return Response( event_stream(), mimetype = 'text/event-stream', headers = { 'Cache-Control': 'no-cache' } )

# Event endpoint

@app.route( '/event/<eid>' ) # we must secrure this shomehow...
def event( eid ):
	e = db.events( [ eid ] )[ 0 ]
	return Response( str( e ), mimetype = 'application/json' )

# Student's endpoints

def student_required( view ): # teacher => student
	@wraps( view )
	def _view( *args, **kwargs ):
		if not ( g.location or g.teacher ): return redirect( url_for( 'student_login' ) )
		return view( *args, **kwargs )
	return _view

@app.route( '/login/<student>/<location>/<secret>', methods = [ 'GET' ] )
@app.route( '/login', methods = [ 'GET', 'POST' ] )
def student_login( student = None, location = None, secret = None ):
	if request.method == 'POST':
		f = request.form
		if not 'location' in f: abort( 500 )
		if not 'student' in f: abort( 500 )
		if not 'secret' in f: abort( 500 )
		location = f[ 'location' ]
		student = f[ 'student' ]
		secret = f[ 'secret' ]
	if request.method == 'GET':
		if not ( student and location and secret ): return render_template( 'login.html' )
	if secret != app.config[ 'SECRET_STUDENTS' ]: abort( 403 )
	session[ 'location' ] = location
	db.login( student, location )
	return redirect( url_for( 'student' ) )

@app.route( '/' )
@student_required
def student():
	return render_template( 'student.html' )

@app.route( '/question', methods = [ 'POST' ] )
@student_required
def question():
	if not 'question' in request.form: abort( 500 )
	db.question( request.form[ 'question' ], g.location )
	return ''

# Teacher's endpoints

def teacher_required( view ):
	@wraps( view )
	def _view( *args, **kwargs ):
		if not g.teacher: return redirect( url_for( 'teacher_login' ) )
		return view( *args, **kwargs )
	return _view

@app.route( '/t/login/<secret>', methods = [ 'GET' ] )
@app.route( '/t/login', methods = [ 'GET', 'POST' ] )
def teacher_login( secret = None ):
	if request.method == 'POST':
		f = request.form
		if not 'secret' in f: abort( 500 )
		secret = f[ 'secret' ]
	if request.method == 'GET':
		if not secret: return render_template( 'tlogin.html' )
	if secret != app.config[ 'SECRET_TEACHER' ]: abort( 403 )
	session[ 'secret' ] = secret
	return redirect( url_for( 'teacher' ) )

@app.route( '/t/answer', methods = [ 'POST' ] )
@teacher_required
def answer():
	f = request.form
	if not 'answer' in f: abort( 500 )
	if not 'kind' in f: abort( 500 )
	if not 'location' in f: abort( 500 )
	db.answer( f[ 'answer' ], f[ 'kind' ], f[ 'location' ] )
	return ''

@app.route( '/t/clear_questions', methods = [ 'POST' ] )
@teacher_required
def clear_questions():
	if not 'location' in request.form: abort( 500 )
	if not db.logged( request.form[ 'location' ] ): abort( 500 )
	db.clear_questions( request.form[ 'location' ] )
	return ''

@app.route( '/t/logout/<location>' )
@teacher_required
def student_logout( location ):
	db.logout( location )
	return redirect( url_for( 'teacher' ) )

@app.route( '/t/<rooms>' )
@app.route( '/t' )
@teacher_required
def teacher( rooms = 'guests' ):
	try:
		t = [ render_template( 'maps/{0}.html'.format( _ ) ) for _ in rooms.split( '+' ) ]
	except TemplateNotFound:
		abort( 404 )
	return render_template( 'teacher.html', rooms = ' '.join( t ) )

# Terminal endpoint

@app.route( '/term' )
@student_required
def term():
	return render_template( 'term.html' )

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
