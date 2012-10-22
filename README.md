# Lavagna

Lavagna (*whiteboar*) is a web application that can be used as a teaching aid
during computer lab lessons. It is a kind of async chat server supporting
private and public messages, syntax highlihting (for code related messages),
and a classroom map to keep track of who is seating where and asking what.

It is based on [Flask](http://flask.pocoo.org/), and uses
[Redis](http://redis.io/) to handle the pub/sub communication.