from json import dumps
import os
from pty import spawn

from redis import StrictRedis

red = StrictRedis( unix_socket_path = './data/redis.sock' )

def read( fd ):
	data = os.read( fd, 1024 )
	red.publish( 'stream:term', dumps( dict( payload = data ) ) )
	return data

if __name__ == '__main__':
	spawn( 'bash', read )
