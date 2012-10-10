import datetime
from flask import Flask, render_template, request, Response
import redis

app = Flask( __name__ )
app.secret_key = 'asdf'
red = redis.StrictRedis( unix_socket_path = './redis/redis.sock' )

@app.route( '/post/<kind>', methods = [ 'POST' ] )
def post( kind ):
	ip = request.remote_addr
	message = request.form[ 'message' ]
	now = datetime.datetime.now().replace(microsecond=0).time()
	data = u'<fieldset><legend>{0}</legend><pre>{1}</pre></fieldset>'.format( now.isoformat(), message );
	red.publish( kind, data )

@app.route( '/stream/<kind>' )
def stream( kind ):
	def event_stream():
		pubsub = red.pubsub()
		pubsub.subscribe( kind )
		for message in pubsub.listen():
			if message[ 'type' ] != 'message': continue
			yield 'data: %s\n\n' % message[ 'data' ]	
	return Response( event_stream(), mimetype = 'text/event-stream' )

@app.route('/s/<room>/<uid>')
def student( room, uid ):
	return render_template( 'student.html', room = room, uid = uid )

@app.route('/t/<room>')
def student( room ):
	return render_template( 'techer.html', room = room )

if __name__ == '__main__':
	app.debug = True
	app.run()
