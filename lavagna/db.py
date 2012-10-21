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
	if ( channel == 'teacher' ):
		for location in red.smembers( 'persist:teacher:questions' ):
			for data in red.lrange( 'persist:teacher:question:{0}'.format( location ), 0, -1 ):
				yield data
	pubsub = red.pubsub()
	pubsub.subscribe( channel )
	for message in pubsub.listen():
		if message[ 'type' ] != 'message': continue
		yield message[ 'data' ]
	
def studentat( location ):
	return red.get( 'studentat:{0}'.format( location ) )

def seat( student, location ):
	if ( student ):
		if studentat( location ) == student: return
		red.set( 'studentat:{0}'.format( location ), student )
		data = dumps( {
			'event': 'seat',
			'student': student,
			'location': location,
		} )
		clear_questions( location )
		red.publish( 'teacher', data )
		red.rpush( 'persist:teacher', data )
	else: # only the teacher can seat empty students
		student = studentat( location )
		if ( not student ): return
		data = dumps( {
			'event': 'seat',
			'student': student,
			'location': location,
		} )
		red.delete( 'studentat:{0}'.format( location ) )
		clear_questions( location )
		red.lrem( 'persist:teacher', 1, data )

def clear_questions( location ):
	red.srem( 'persist:teacher:questions', location )
	red.ltrim( 'persist:teacher:question:{0}'.format( location ), 1, 0 ) # start > end => delete

def question( question, location ):
	if ( not question ): # only the teacher can post empty questions
		clear_questions( location )
		return
	data = dumps( {
		'event': 'question',
		'student': studentat( location ),
		'location': location,
		'question': question,
		'now': now()
	} )
	red.publish( 'teacher', data )
	red.sadd( 'persist:teacher:questions', location )
	red.rpush( 'persist:teacher:question:{0}'.format( location ), data )

def answer( answer, kind, destination ):
	data = dumps( {
		'answer': answer,
		'kind': kind,
		'destination': destination,
		'now': now()
	} )
	red.publish( 'student', data )
	red.rpush( 'persist:student', data )
