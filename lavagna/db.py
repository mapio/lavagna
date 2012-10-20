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

def studentat( location ):
	return red.get( 'studentat:{0}'.format( location ) )

def seated():
	return dict( ( _, studentat( _ ) ) for _ in red.smembers( 'busylocations' ) )

def question( message, location ):
	data = {
		'location': location,
		'student': studentat( location ),
		'message': message,
		'now': now()
	}
	red.publish( 'questions', dumps( data ) )

def answer( message, kind, destination ):
	data = {
		'message': message,
		'kind': kind,
		'destination': destination,
		'now': now()
	}
	red.publish( 'answers', dumps( data ) )
