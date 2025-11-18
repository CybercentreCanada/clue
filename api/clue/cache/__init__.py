from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, Self

from flask import Flask
from flask_caching import Cache as FlaskCache
from pydantic import TypeAdapter

from clue.common.logging import get_logger
from clue.config import get_redis
from clue.models.network import QueryEntry
from clue.remote.datatypes.hash import ExpiringHash

if TYPE_CHECKING:
    from clue.plugin.utils import Params

logger = get_logger(__file__)


class Cache:
    "Caching wrapped for local/redis cache"

    __type: Literal["redis"] | Literal["local"]
    __local_cache: FlaskCache | None
    __redis_cache: ExpiringHash | None
    __app: Flask

    def __init__(
        self: Self,
        cache_name: str,
        app: Flask,
        type: Literal["redis"] | Literal["local"],
        timeout: int = 5 * 60,  # five minute timeout
        local_cache_options: dict[str, Any] | None = None,
    ):
        self.__app = app
        self.__type = type

        logger.debug("Enabling cache, type %s", self.__type)
        if self.__type == "local":
            self.__local_cache = FlaskCache(
                self.__app,
                config=(
                    local_cache_options
                    if local_cache_options is not None
                    else {"CACHE_TYPE": "SimpleCache", "CACHE_DEFAULT_TIMEOUT": timeout}
                ),
            )
        else:
            self.__redis_cache = ExpiringHash(cache_name, host=get_redis(), ttl=timeout)

    def __generate_hash(self: Self, type_name: str, value: str, params: "Params") -> str:
        "Generate a sha256 hash based on the selector"
        hash_data = sha256(type_name.encode())
        hash_data.update(value.encode())

        hash_data.update(str(params.annotate).encode())
        hash_data.update(str(params.raw).encode())
        hash_data.update(str(params.limit).encode())

        key = hash_data.hexdigest()

        return key

    def set(self: Self, type_name: str, value: str, params: "Params", data: list[QueryEntry]):
        "Add the result of a given enrichment to the cache"
        key = self.__generate_hash(type_name, value, params)

        try:
            serialized_data = TypeAdapter(list[QueryEntry]).dump_python(
                data, mode="json", exclude_none=True, exclude_unset=True
            )

            if self.__type == "local":
                if self.__local_cache is None:
                    logger.warning("Local cache is None despite type being local")
                    return

                self.__local_cache.set(key, serialized_data)
            else:
                if self.__redis_cache is None:
                    logger.warning("Redis cache is None despite type being redis")
                    return

                self.__redis_cache.set(key, serialized_data)
        except Exception:
            logger.exception("Error on retrieval")
            return None

    def get(self: Self, type_name: str, value: str, params: "Params") -> list[QueryEntry] | None:
        "Add the result of a given enrichment to the cache"
        key = self.__generate_hash(type_name, value, params)

        try:
            if self.__type == "local":
                if self.__local_cache is None:
                    return None

                cached_result = self.__local_cache.get(key)
            else:
                if self.__redis_cache is None:
                    return None

                cached_result = self.__redis_cache.get(key)

            if not cached_result:
                return None

            if not isinstance(cached_result, list):
                cached_result = [cached_result]

            return TypeAdapter(list[QueryEntry]).validate_python(cached_result)
        except Exception:
            logger.exception("Error on cache retrieval")
            return None

    def delete(self: Self, type_name: str, value: str, params: "Params"):
        "Remove data associated with a key from the cache"
        key = self.__generate_hash(type_name, value, params)

        try:
            if self.__type == "local":
                if self.__local_cache:
                    self.__local_cache.delete(key)
            else:
                if self.__redis_cache:
                    self.__redis_cache.pop(key)
        except Exception:
            logger.exception("Error on cache deletion")
            return None
