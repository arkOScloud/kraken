"""
Classes and functions to manage Redis data storage.

arkOS Kraken
(c) 2016 CitizenWeb
Written by Jacob Cook
Licensed under GPLv3, see LICENSE.md
"""

import json
import redis

from arkos.utilities.errors import ConnectionError


class Storage:
    """Manage connection and interface with Redis."""

    def __init__(self):
        """Initialize."""
        self.connect()

    def connect(self):
        """Connect to Redis server."""
        try:
            self.redis = redis.Redis(unix_socket_path="/tmp/arkos-redis.sock")
            self.redis.ping()
            self.redis.flushdb()
        except redis.exceptions.ConnectionError:
            raise ConnectionError("arkOS Redis")

    def disconnect(self):
        """Disconnect from Redis server."""
        self.redis.flushdb()
        self.redis.connection_pool.disconnect()

    def check(self):
        """
        Make sure our connection to Redis is still active.

        If not, stop everything, reconnect and reload.
        """
        try:
            self.redis.ping()
        except:
            self.connect()

    def get(self, key, optkey=None):
        """
        Get a value from a Redis key or hash.

        :param str key: Key name
        :param str optkey: Hash key name (optional)
        """
        self.check()
        if optkey:
            return self._get(self.redis.hget("arkos:{0}".format(key), optkey))
        else:
            return self._get(self.redis.get("arkos:{0}".format(key)))

    def get_all(self, key):
        """
        Get all keys and values from a hash.

        :param str key: Key name
        """
        values = self.redis.hgetall("arkos:{0}".format(key))
        for x in values:
            values[x] = self._get(values[x])
        return values

    def set(self, key, value, optval=None, pipe=None):
        """
        Set a key value or hash value, or push to a list.

        :param str key: Key name
        :param value: Hash key name OR value to set/push to key
        :param optval: Hash key value (optional)
        :param pipe: Pipe to queue operations on
        """
        self.check()
        r = pipe or self.redis
        if optval:
            r.hset("arkos:{0}".format(key), value, optval)
        elif type(value) == list:
            for x in enumerate(value):
                if type(x[1]) in [list, dict]:
                    value[x[0]] = json.dumps(x[1])
            r.rpush("arkos:{0}".format(key), *value)
        elif type(value) == dict:
            for x in value:
                if type(value[x]) in [list, dict]:
                    value[x] = json.dumps(value[x])
            r.hmset("arkos:{0}".format(key), value)
        else:
            r.set("arkos:{0}".format(key), value)

    def pop(self, key, pipe=None):
        """
        Remove and return a value from a list.

        :param str key: Key name
        :param pipe: Pipe to queue operations on
        :returns: List value
        """
        r = pipe or self.redis
        return self._get(r.lpop("arkos:{0}".format(key)))

    def get_list(self, key):
        """
        Return an entire list.

        :param str key: Key name
        :returns: list
        """
        self.check()
        values = []
        for x in self.redis.lrange("arkos:{0}".format(key), 0, -1):
            values.append(self._get(x))
        return values

    def append(self, key, value, pipe=None):
        """
        Append a value to a list.

        :param str key: Key name
        :param value: Value to push to list
        :param pipe: Pipe to queue operations on
        """
        self.check()
        r = pipe or self.redis
        if type(value) in [list, dict]:
            value = json.dumps(value)
        r.rpush("arkos:{0}".format(key), value)

    def append_all(self, key, values, pipe=None):
        """
        Append multiple values to a list.

        :param str key: Key name
        :param list values: Values to push to list
        :param pipe: Pipe to queue operations on
        """
        if values:
            r = pipe or self.redis.pipeline()
            self.check()
            values = list(values)
            for x in enumerate(values):
                if type(x[1]) in [list, dict]:
                    values[x[0]] = json.dumps(x[1])
            r.rpush("arkos:{0}".format(key), *values)
            if not pipe:
                r.execute()

    def set_list(self, key, values, pipe=None):
        """
        Set a Redis list to match the provided list.

        :param str key: Key name
        :param list values: Values to set list as
        :param pipe: Pipe to queue operations on
        """
        if values:
            r = pipe or self.redis.pipeline()
            r.delete("arkos:{0}".format(key))
            self.append_all(key, values, pipe=r)
            if not pipe:
                r.execute()

    def sortlist_add(self, key, priority, value, pipe=None):
        """
        Add a value to a sorted list.

        :param str key: Key name
        :param int priority: Priority of list placement
        :param str value: Value to push to list
        :param pipe: Pipe to queue operations on
        """
        self.check()
        r = pipe or self.redis
        if type(value) in [list, dict]:
            value = json.dumps(value)
        r.zadd("arkos:{0}".format(key), value, priority)

    def sortlist_getbyscore(self, key, priority, num=0, pop=False):
        """
        Retrieve values from a sorted list by priority.

        :param str key: Key name
        :param int priority: Priority floor of list placement
        :param int num: Max number of values to return
        :param bool pop: Remove value from list after obtaining?
        :returns: Sorted list values
        """
        self.check()
        data = self.redis.zrevrangebyscore("arkos:{0}".format(key), priority,
                                           num)
        if pop:
            self.redis.zremrangebyscore("arkos:{0}".format(key), num, priority)
        return self._get(data)

    def remove(self, key, value, pipe=None):
        """
        Remove value from list.

        :param str key: Key name
        :param str value: Value to remove from list
        :returns: Sorted list values
        """
        r = pipe or self.redis
        newvals = []
        for x in self.get_list(key):
            x = self._get(x)
            if x == value:
                continue
            newvals.append(x)
        self.delete(key, pipe=r)
        self.append_all(newvals, pipe=r)

    def remove_all(self, key, values, pipe=None):
        """
        Remove multple values from list.

        :param str key: Key name
        :param str values: Values to remove from list
        :returns: Sorted list values
        """
        r = pipe or self.redis
        newvals = []
        for x in self.get_list(key):
            x = self._get(x)
            if x in values:
                continue
            newvals.append(x)
        self.delete(key, pipe=r)
        self.append_all(newvals, pipe=r)

    def delete(self, key, pipe=None):
        """
        Delete key.

        :param str key: Key name
        :returns: Sorted list values
        """
        self.check()
        r = pipe or self.redis
        r.delete("arkos:{0}".format(key))

    def scan(self, key):
        """
        Get a list of keys present that match the provided pattern.

        :param str key: Key name pattern
        :returns: List of key names
        """
        return self.redis.scan(0, "arkos:{0}".format(key))[1]

    def pipeline(self):
        """Create a set of Redis commands."""
        return self.redis.pipeline()

    def execute(self, pipe):
        """Execute a set of commands."""
        pipe.execute()

    def expire(self, key, time, pipe=None):
        """
        Set a key's time until expiry.

        :param str key: Key name
        :param int time: Time in seconds until expiry
        :param pipe: Pipe to queue operations on
        """
        r = pipe or self.redis
        r.expire("arkos:{0}".format(key), time)

    def _get(self, value):
        if type(value) == str:
            return self._translate(value)
        elif type(value) == list:
            vals = []
            for x in value:
                vals.append(self._translate(x))
            return vals
        return value

    def _translate(self, value):
        if value.startswith(("[", "{")) and value.endswith(("]", "}")):
            return json.loads(value)
        return value


storage = Storage()
