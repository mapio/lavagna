from cgi import escape 
from json import dumps, loads
from datetime import datetime

from redis import StrictRedis

red = StrictRedis( unix_socket_path = './data/redis.sock' )

def now():
	return datetime.now().replace( microsecond = 0 ).time().isoformat()
	
def seat( student, location ):
	red.set( 'studentat:{0}'.format( location ), student )
	red.sadd( 'busylocations', location )
	data = {
		'event': 'seat',
		'student': studentat( location ),
		'location': location,		
		'now': now()
	}
	red.publish( 'teacher', dumps( data ) )

def studentat( location ):
	return red.get( 'studentat:{0}'.format( location ) )

def seated():
	return dict( ( _, studentat( _ ) ) for _ in red.smembers( 'busylocations' ) )

def question( question, location ):
	data = {
		'event': 'question',
		'student': studentat( location ),
		'location': location,
		'question': question,
		'now': now()
	}
	red.publish( 'teacher', dumps( data ) )

def answer( answer, kind, destination ):
	data = {
		'answer': answer,
		'kind': kind,
		'destination': destination,
		'now': now()
	}
	red.publish( 'student', dumps( data ) )
