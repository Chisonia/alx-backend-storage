#!/usr/bin/env python3
'''This module contains the Cache class that stores
data using a random key'''
import redis
import uuid
from typing import Any, Union, Callable, Optional
from functools import wraps


def replay(method: Callable):
    '''
     display the history of calls of a particular function
     '''
    method_name = method.__qualname__
    count = method.__self__._redis.llen(f"{method_name}:inputs")
    print(f"{method_name} was called {count} times:")

    inputs = method.__self__._redis.lrange(f"{method_name}:inputs", 0, -1)
    outputs = method.__self__._redis.lrange(f"{method_name}:outputs", 0, -1)

    for input_val, output_val in zip(inputs, outputs):
        # Decode input and format it correctly
        print(f"{method_name}(*{eval(input_val.decode('utf-8'))}) -> {output_val.decode('utf-8')}")  # noqa: E501


def call_history(method: Callable) -> Callable:
    '''
    Store the history of inputs and
    outputs for a particular function.
    '''
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        inputs_key = f"{method.__qualname__}:inputs"
        outputs_key = f"{method.__qualname__}:outputs"

        self._redis.rpush(inputs_key, str(args))

        output = method(self, *args, **kwargs)

        self._redis.rpush(outputs_key, str(output))
        return output
    return wrapper


def count_calls(method: Callable) -> Callable:
    ''''
    Counts how many times a method is called using Redis.
    '''
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        '''increment the count in Redis for this method
        qualified name'''
        key = method.__qualname__
        self._redis.incr(key)
        return method(self, *args, **kwargs)
    return wrapper


class Cache:
    def __init__(self):
        '''
        Initialize the Redis client and flush the database
        '''
        self._redis = redis.Redis()
        self._redis.flushdb()

    @call_history
    @count_calls
    def store(self, data: Union[str, bytes, int, float]) -> str:
        '''Stores data in Redis with a randomly generated key
        data: data to store (str, bytes, int, or float) as str
        and returns the key under which the data is stored.
        '''
        # generate a unique key
        key = str(uuid.uuid4())
        # store the data in Redis
        self._redis.set(key, data)
        return key

    def get(self, key: str, fn: Optional[Callable] = None) -> Union[str, bytes, int, float, None]:  # noqa: E501
        '''
        Retieves data from Redis and applies optional conversion function.
        key: retieves ke while fn is the an optional
        callable to convert the data
        and returns possibly converted data retrieved from Redis
        '''
        data = self._redis.get(key)

        if data is None:
            return None
        return fn(data) if fn else data

    def get_str(self, key: str) -> Union[str, None]:
        '''
        Retrieve data as a UTF-8 decoded string.
        Key is the key retrieved.
        and returns the data as UTF-8 string, or None if
        key does not exist
        '''
        return self.get(key, fn=lambda d: d.decode("utf-8"))

    def get_int(self, key: str) -> Union[int, None]:
        '''
        Retrieve data as an integer.
        retrieve key and returns data as an integer, or None if the
        key does not exist.'''
        return self.get(key, fn=int)
