from json import JSONDecodeError
from json import dumps
from json import loads
from typing import Protocol

from atomic_filesystem_lib import FilesystemProtocol
from typed_accessor_lib import TypedAccessor
from typed_accessor_lib import TypedAccessorError
from virtual_path_lib import VirtualPath


class JsonAccessorError(Exception):
    """Base class for exceptions in this module."""


class JsonDecodeError(JsonAccessorError):
    """Bad JSON data."""


class JsonReadError(JsonAccessorError):
    """Filesystem problem with reading file."""


class JsonAccessor(Protocol):
    """Protocol for accessing JSON data."""

    def read[T: int | str](
        self,
        path: VirtualPath,
        key_type: type[T] = int | str,
    ) -> TypedAccessor[T]:
        """
        Reads JSON data from `path`. Parameter `key_type`
        is expected root JSON type: `int` for array, `str` for object.
        Raises `JsonReadError` if file not exists, or any other filesystem error.
        Raises `JsonDecodeError` if file not a JSON array or object or has errors.
        Raises `JsonAccessorError` for any unknown error.
        """
        raise NotImplementedError()

    def write(
        self,
        path: VirtualPath,
        data: dict | list,
    ) -> None:
        """
        Writes or overwrites JSON `data` to `path`.
        Raises `JsonWriteError` if `path` is a directory, or any other filesystem error.
        Raises `JsonAccessorError` for any unknown error.
        """
        raise NotImplementedError()


class FilesystemJsonAccessor:
    """JSON accessor for real filesystem."""

    def __init__(self, fs: FilesystemProtocol):
        self._fs: FilesystemProtocol = fs

    def read[T: int | str](
        self,
        path: VirtualPath,
        key_type: type[T] = int | str,
    ) -> TypedAccessor[T]:
        """
        Reads JSON data from `path`. Parameter `key_type`
        is expected root JSON type: `int` for array, `str` for object.
        Raises `JsonReadError` if file not exists, or any other filesystem error.
        Raises `JsonDecodeError` if file not a JSON array or object or has errors.
        Raises `JsonAccessorError` for any unknown error.
        """
        if key_type is int:
            source_type = list
        elif key_type is str:
            source_type = dict
        else:
            source_type = dict | list

        try:
            json = b"".join(self._fs.load_file(path))
            return TypedAccessor[T](loads(json), source_type)
        except JSONDecodeError as json_error:
            raise JsonDecodeError("Can not decode JSON %s. %s" % (path, json_error))
        except TypedAccessorError as json_error:
            raise JsonDecodeError("Can not decode JSON %s. %s" % (path, json_error))
        except OSError as os_error:
            raise JsonReadError("Can not read JSON %s. %s" % (path, os_error))
        except Exception as unknown_error:
            raise JsonAccessorError("Error reading JSON %s. %s" % (path, unknown_error))

    def write(self, path: VirtualPath, data: dict | list) -> None:
        """
        Writes or overwrites JSON `data` to `path`.
        Not raises `JsonWriteError` because of filesystem commiting function.
        Raises `JsonAccessorError` for any unknown error.
        """
        try:
            self._fs.save_file(
                path,
                dumps(
                    data,
                    ensure_ascii=False,
                    indent="\t",
                    sort_keys=True,
                ),
            )
        except Exception as unknown_error:
            raise JsonAccessorError("Error writing JSON %s. %s" % (path, unknown_error))


class MemoryJsonAccessor:
    """JSON accessor for unit-testing."""

    def __init__(self, data: dict[str, object] | None = None):
        self.data: dict[str, str] = {k: dumps(v) for k, v in (data or dict()).items()}

    def read[T: int | str](
        self,
        path: VirtualPath,
        key_type: type[T] = int | str,
    ) -> TypedAccessor[T]:
        """
        Reads JSON data from `path`. Parameter `key_type`
        is expected root JSON type: `int` for array, `str` for object.
        Raises `JsonReadError` if file not exists.
        Raises `JsonDecodeError` if file not a JSON array or object or has errors.
        Raises `JsonAccessorError` for any unknown error.
        """
        if key_type is int:
            source_type = list
        elif key_type is str:
            source_type = dict
        else:
            source_type = dict | list

        try:
            json = self.data[str(path)]
            return TypedAccessor[T](loads(json), source_type)
        except KeyError as os_error:
            raise JsonReadError("Can not read JSON %s. %s" % (path, os_error))
        except TypedAccessorError as json_error:
            raise JsonDecodeError("Can not decode JSON %s. %s" % (path, json_error))

    def write(self, path: VirtualPath, data: dict | list) -> None:
        """
        Writes or overwrites JSON `data` to `path`.
        Not raises `JsonWriteError`.
        Raises `JsonAccessorError` for any unknown error.
        """
        try:
            self.data[str(path)] = dumps(data)
        except Exception as unknown_error:
            raise JsonAccessorError("Error writing JSON %s. %s" % (path, unknown_error))
