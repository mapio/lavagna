from cgi import escape 
from json import dumps, loads
from datetime import datetime

from redis import StrictRedis

red = StrictRedis( unix_socket_path = './data/redis.sock' )

def now():
	return datetime.now().replace( microsecond = 0 ).time().isoformat()

def messages( channel ):
	for data in red.lrange( 'persist:{0}'.format( channel ), 0, -1 ):
		yield data
	pubsub = red.pubsub()
	pubsub.subscribe( channel )
	for message in pubsub.listen():
		if message[ 'type' ] != 'message': continue
		yield message[ 'data' ]
	
def studentat( location ):
	return red.get( 'studentat:{0}'.format( location ) )

def seat( student, location ):
	red.set( 'studentat:{0}'.format( location ), student )
	data = dumps( {
		'event': 'seat',
		'student': studentat( location ),
		'location': location,		
		'now': now()
	} )
	red.publish( 'teacher', data )
	red.rpush( 'persist:teacher', data )

def question( question, location ):
	data = dumps( {
		'event': 'question',
		'student': studentat( location ),
		'location': location,
		'question': question,
		'now': now()
	} )
	red.publish( 'teacher', data )

def answer( answer, kind, destination ):
	data = dumps( {
		'answer': answer,
		'kind': kind,
		'destination': destination,
		'now': now()
	} )
	red.publish( 'student', data )
	red.rpush( 'persist:student', data )