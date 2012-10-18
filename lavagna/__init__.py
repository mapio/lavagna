from cgi import escape 
import datetime

from flask import Flask, render_template, request, Response, abort

import redis

app = Flask( __name__ )
red = redis.StrictRedis( unix_socket_path = './data/redis.sock' )

def now():
	return datetime.datetime.now().replace( microsecond = 0).time().isoformat()
	
def identify( uid, ip ):
	student = red.get( 'student:{0}'.format( uid ) )
	location = red.get( 'location:{0}'.format( ip ) )
	return student, location

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

@app.route( '/post/question/<uid>', methods = [ 'POST' ] )
def post_question( uid ):
	student, location = identify( uid, request.remote_addr )
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

@app.route( '/s/<room>/<uid>' )
def student( room, uid ):
	print request.remote_addr
	student, location = identify( uid, request.remote_addr )
	print student, location	
	if not student or not location: abort( 404 )
	return render_template( 'student.html', room = room, location = location, student = student )

@app.route( '/t/<room>' )
def teacher( room ):
	return render_template( 'teacher.html', room = room )

@app.route( '/map' )
def map():
	return render_template( 'map.html', ipmap = IPS	 )

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
