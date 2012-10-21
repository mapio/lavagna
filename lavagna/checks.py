from json import dumps, loads

from redis import StrictRedis

from db import events

red = StrictRedis( unix_socket_path = './data/redis.sock' )

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

if __name__ == '__main__':
	print 'Application secret:', red.get( 'secret:application' )
	print 'Teacher secret:', red.get( 'secret:teacher' )
	check_events()
	check_logins()
	print 'Questions:'
	check_active( 'questions' )
	print 'Answers:'
	check_active( 'answers' )
