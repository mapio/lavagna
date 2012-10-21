from cgi import escape 
from json import dumps, loads
from datetime import datetime

from redis import StrictRedis

red = StrictRedis( unix_socket_path = './data/redis.sock' )

def now():
	return datetime.now().replace( microsecond = 0 ).time().isoformat()

def secret( realm ):
	return red.get( 'secret:{0}'.format( realm ) )

def events( eids ):
	keys = [ 'events:id:{0}'.format( i ) for i in eids ]
	if keys: return red.mget( *keys )
	return []

def publish( data ):
	eid = red.incr( 'events:id' )
	data[ 'eid' ] = eid
	data[ 'now' ] = now()
	jdata = dumps( data )
	red.set( 'events:id:{0}'.format( eid ), jdata )
	event = data[ 'event' ]
	if event == 'answer':
		red.publish( 'stream:student', jdata )
	else:
		red.publish( 'stream:teacher', jdata )
	if event == 'login':
		student, location = data[ 'student' ], data[ 'location' ]
		red.sadd( 'logins:*', eid )
		red.set( 'login:{0}'.format( location ), eid )
		red.delete( 'questions:{0}'.format( location ) )
		red.delete( 'answers:{0}'.format( location ) )
	elif event == 'logout':
		location = data[ 'location' ]
		eid_todel = red.get( 'login:{0}'.format( location ) )
		red.srem( 'logins:*', eid_todel )
		red.delete( 'login:{0}'.format( location ) )
		red.delete( 'questions:{0}'.format( location ) )
		red.delete( 'answers:{0}'.format( location ) )
	elif event == 'question':
		location = data[ 'location' ]
		red.sadd( 'questions:{0}'.format( location ), eid )
	elif event == 'clear_questions':
		location = data[ 'location' ]
		red.delete( 'questions:{0}'.format( location ) )
	elif event == 'answer':
		location = data[ 'location' ]
		red.sadd( 'answers:{0}'.format( location ), eid )
	else: raise RuntimeError( 'Unknown event: {0}'.format( event ) )

def retrieve( stream, location = None ):
	if stream == 'student':
		broadcasted = red.smembers( 'answers:*' )
		private = red.smembers( 'answers:{0}'.format( location ) )
		for event in events( sorted( broadcasted | private ) ):
			yield event
	elif stream == 'teacher':
		questions = set()
		for event in events( red.smembers( 'logins:*' ) ):
			location = loads( event )[ 'location' ]
			questions |= red.smembers( 'questions:{0}'.format( location ) )
			yield event
		for event in events( sorted( questions, reverse = True ) ):
			yield event
	else: raise RuntimeError( 'Unknown stream: {0}'.format( stream ) )
	pubsub = red.pubsub()
	pubsub.subscribe( 'stream:{0}'.format( stream ) )
	for message in pubsub.listen():
		if message[ 'type' ] != 'message': continue
		yield message[ 'data' ]

def logged( location ):
	eid = red.get( 'login:{0}'.format( location ) )
	if not eid: return None
	student = loads( red.get( 'events:id:{0}'.format( eid ) ) )[ 'student' ]
	return student

def login( student, location ):
	if logged( location ) == student: return
	publish( {
		'event': 'login',
		'student': student,
		'location': location,
	} )

def logout( location ):
	student = logged( location )
	if ( not student ): return
	publish( {
		'event': 'logout',
		'student': student,
		'location': location,
		'login_eid': red.get( 'login:{0}'.format( location ) )
	} )

def clear_questions( location ):
	publish( {
		'event': 'clear_questions',
		'location': location
	} )

def question( question, location ):
	publish( {
		'event': 'question',
		'student': logged( location ),
		'location': location,
		'question': question
	} )

def answer( answer, kind, location ):
	publish( {
		'event': 'answer',
		'location': location,
		'answer': answer,
		'kind': kind
	} )

if __name__ == '__main__':
	
	def check( eid, event = None, location = None ):
		eid = int( eid )
		data = loads( events( [ eid ] )[ 0 ] )
		if ( data[ 'eid' ] == eid and 
			( ( event and data[ 'event' ] == event ) or not event ) and
			( ( location and data[ 'location' ] == location ) or not location ) ):
			del data[ 'eid' ]
			event = data[ 'event' ] 
			del data[ 'event' ]
			now = data[ 'now' ]
			del data[ 'now' ]
			location = data[ 'location' ]
			del data[ 'location' ]
			return '\t'.join( map( str, [ eid, now, event, location, data ] ) )
		else:
			return eid, None
	
	def check_active( event ):
		for key in red.keys( '{0}:*'.format( event ) ):
			fevent, flocation = key.split( ':' )
			fevent = fevent[ : -1 ]
			for eid in red.smembers( key ):
				print '\t', check( eid, fevent, flocation )

	def check_logins():
		print 'Logins:'
		computed_active_eids = dict(
			( red.get( key ), key.split( ':' )[ 1 ] ) for key in red.keys( 'login:*' )
		)
		active_eids = red.smembers( 'logins:*' )
		sym_diff = set( computed_active_eids.keys() ).symmetric_difference( active_eids )
		if sym_diff: raise RuntimeError( 'sym_diff', sym_diff )
		for eid, location in computed_active_eids.items():
			print '\t', check( eid, 'login', location )

	def check_events():
		max_eid = int( red.get( 'events:id' ) )
		event_ids = set( red.keys( 'events:id:*' ) )
		sym_diff = event_ids.symmetric_difference( set( 'events:id:{0}'.format( i ) for i in range( 1, 1 + max_eid ) ) )
		if sym_diff: raise RuntimeError( 'sym_diff', sym_diff )
		print 'Events:'
		for eid, event in enumerate( events( range( 1, 1 + max_eid ) ) ):
			print '\t', check( eid + 1 )
			
	print 'Application secret:', red.get( 'secret:application' )
	print 'Teacher secret:', red.get( 'secret:teacher' )
	check_events()
	check_logins()
	print 'Questions:'
	check_active( 'questions' )
	print 'Answers:'
	check_active( 'answers' )
