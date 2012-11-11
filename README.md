# Lavagna

Lavagna (*whiteboard*) is a web application that can be used as a teaching aid
during computer lab lessons. It is a kind of async chat server supporting
private and public messages, syntax highlihting (for code related messages),
and a classroom map to keep track of who is seating where and asking what.

It is based on [Flask](http://flask.pocoo.org/) and [Redis](http://redis.io/)
to handle the pub/sub communication; it can be served by any async webserver,
for instance [gunicorn](http://gunicorn.org/) (using
[libevent](http://libevent.org/) based workers).

The async communication among the server and browser uses [Server-sent
events](https://developer.mozilla.org/en-US/docs/Server-sent_events).

## A test run

First of all, install the dependencies (`redis`, `libevenvt` and the Python
packages listed in `requirements.txt`), then issue the following commands:

```bash

	./bin/redis start
	./bin/set_secrets
	./bin/gunicorn start
	./bin/tlogin localhost:8000
	./bin/login 'Test student' guest-0 localhost:8000
```

Lavagna supports terminal broadcasting (full XTerm support thanks to
[tty.js](https://github.com/chjj/tty.js/)) and pasting of image messages (via
[Clipboard API](http://dev.w3.org/2006/webapi/clipops/clipops.html)).

You can test terminal broadcasting issuing the command:

```bash

	./bin/term localhost:8000
```

Moreover, you can get notification of student questions via [Prowl](http://www.prowlapp.com/).


## Screenshots

This is the teacher view of a "Guest" classroom where a student as posed a question:

![Teacher view](https://raw.github.com/mapio/lavagna/master/screenshots/teacher.png)

Here is the "Test student" view, the first is a broadcast message, the second
one is the private answer to his question:

![Student view](https://raw.github.com/mapio/lavagna/master/screenshots/student.png)

Finally, an example of terminal broadcasting: the back window is a terminal showing the
exact same content of the terminal running in the front window.

![Terminal broadcasting](https://raw.github.com/mapio/lavagna/master/screenshots/term.png)
