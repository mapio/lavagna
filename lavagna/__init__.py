from cgi import escape 
import datetime

from flask import Flask, render_template, request, Response

import redis

app = Flask( __name__ )
red = redis.StrictRedis( unix_socket_path = './redis/redis.sock' )

@app.route( '/post/<channel>/<kind>', methods = [ 'POST' ] )
def post( channel, kind ):
	ip = request.remote_addr
	message = request.form[ 'message' ]
	now = datetime.datetime.now().replace(microsecond=0).time().isoformat()
	if ( kind != 'html' ):
		message = escape( message )
	if ( kind == 'text' ):
		content = '<pre style="white-space: pre-wrap;">{0}</pre>'.format( message )
	elif ( kind == 'code' ):
		content = '<pre class="pp">{0}</pre>'.format( message )
	else:
		content = message
	red.publish( channel, u'<fieldset><legend>{0}</legend>{1}</fieldset>'.format( now, content ) )
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

@app.route('/s/<room>/<uid>')
def student( room, uid ):
	return render_template( 'student.html', room = room, student = uid )

@app.route('/t/<room>')
def teacher( room ):
	return render_template( 'teacher.html', room = room )

if __name__ == '__main__':
	app.debug = True
	app.run( port = 8000 )
