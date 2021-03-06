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


# The DB contains the follwing keys:
#
# secret:students
# secret:teacher
# secret-prowl
#	the secrets used to authenitcate the clients of this app
#
# events:id
# 	a counter contaning the number of the last seen event
# events:id:<id>
# 	a json-encoded version of the <id> event
#
# logins:*
# 	a set of loing events <id>s
# login:<location>
#	the name of the student currently logged in at <location>
# questions:<location>
#	a set of question events <id>s posted at <locaiton> by the currently logged in student
# answers:<location>
#	a set of answer event <id>s addressed to <location> ('*' is used for broadcast answers)
#
# Moreover, the following pub/sub channels are active
#
# stream:student
# stream:teacher
# stream:term


from json import dumps, loads
from datetime import datetime

from flask import url_for
from prowlpy import Prowl
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

def push( stream, data ):
	red.publish( 'stream:{0}'.format( stream ), data )

def publish( data ):
	eid = red.incr( 'events:id' )
	data[ 'eid' ] = eid
	data[ 'now' ] = now()
	jdata = dumps( data )
	red.set( 'events:id:{0}'.format( eid ), jdata )
	event = data[ 'event' ]
	if event == 'answer': push( 'student', jdata )
	else: push( 'teacher', jdata )
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
		if publish.prowl:
			publish.prowl(
				'Lavagna',
				'Question',
				'{0}: {1}'.format( location, data[ 'question' ] ), 1, url = url_for( 'event', eid = eid, _external = True )
			)
	elif event == 'clear_questions':
		location = data[ 'location' ]
		red.delete( 'questions:{0}'.format( location ) )
	elif event == 'answer':
		location = data[ 'location' ]
		red.sadd( 'answers:{0}'.format( location ), eid )
	else: raise RuntimeError( 'Unknown event: {0}'.format( event ) )
publish.prowl = Prowl( secret( 'prowl' ) ).post if secret( 'prowl' ) else None

def follow( stream ):
	pubsub = red.pubsub()
	pubsub.subscribe( 'stream:{0}'.format( stream ) )
	for message in pubsub.listen():
		if message[ 'type' ] != 'message': continue
		yield message[ 'data' ]

def retrieve( stream, location = None ):
	if stream == 'student': # should we raise an error if location is None here?
		broadcasted = red.smembers( 'answers:*' )
		private = red.smembers( 'answers:{0}'.format( location ) )
		for event in events( sorted( map( int, broadcasted | private ) ) ):
			yield event
	elif stream == 'teacher':
		questions = set()
		for event in events( red.smembers( 'logins:*' ) ):
			location = loads( event )[ 'location' ]
			questions |= red.smembers( 'questions:{0}'.format( location ) )
			yield event
		for event in events( sorted( map( int, questions ) ) ):
			yield event
	else: raise RuntimeError( 'Unknown stream: {0}'.format( stream ) )
	for event in follow( stream ): yield event

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

def term( payload ):
	push( 'term', payload )
