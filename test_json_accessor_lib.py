from unittest import TestCase

from atomic_filesystem_lib import MemoryFilesystem
from typed_accessor_lib import TypedAccessor
from virtual_path_lib import VirtualPath

from json_accessor_lib import FilesystemJsonAccessor
from json_accessor_lib import JsonAccessorError
from json_accessor_lib import JsonDecodeError
from json_accessor_lib import JsonReadError
from json_accessor_lib import MemoryJsonAccessor


def _fs(
    data: dict | None = None,
    context: MemoryFilesystem | None = None,
    root: VirtualPath | None = None,
) -> MemoryFilesystem:
    fs = MemoryFilesystem() if context is None else context
    top = VirtualPath() if root is None else root
    buffer = [(top, data or dict())]
    while buffer:
        t, d = buffer.pop()
        for k, v in d.items():
            p = t.append(k)
            fs.create_file(p, v)
    fs.commit()
    return fs


def _filesystem_json(fs: MemoryFilesystem) -> FilesystemJsonAccessor:
    return FilesystemJsonAccessor(fs)


def _memory_json(data: dict[str, object] | None = None) -> MemoryJsonAccessor:
    return MemoryJsonAccessor(data)


def _path(data: str = "") -> VirtualPath:
    return VirtualPath(data)


def _read_all(accessor: TypedAccessor) -> dict | list:
    result_dict = {}
    result_list = []
    for k in accessor.get_remaining_keys():
        value = accessor.extract_value(k)
        if isinstance(k, str):
            result_dict[k] = value
        else:
            result_list.append(value)
    return result_dict or result_list


class MemoryJsonAccessorTest(TestCase):
    PATH: str = "path"

    def test_read(self) -> None:
        test_list: list[tuple[str, object, str, type[int | str], object]] = [
            ("fail if not dict", [], self.PATH, str, JsonDecodeError),
            ("fail if not exists", [], "n", int, JsonReadError),
            ("fail if not list", {"1": 2}, self.PATH, int, JsonDecodeError),
            ("read dict", {"1": 2}, self.PATH, str, {"1": 2}),
            ("read list", [1, 2], self.PATH, int, [1, 2]),
        ]

        for test in test_list:
            with self.subTest("should %s" % (test[0],)):
                testing = _memory_json({self.PATH: test[1]})
                expected = test[4]
                if isinstance(expected, type) and issubclass(expected, Exception):
                    with self.assertRaises(expected):
                        testing.read(_path(test[2]), test[3])
                else:
                    result = testing.read(_path(test[2]), test[3])
                    self.assertEqual(expected, _read_all(result))

    def test_write(self) -> None:
        with self.subTest("should replace previously written"):
            t = _memory_json({self.PATH: {"1": 1}})
            t.write(_path(self.PATH), {"1": 2})
            self.assertEqual({"1": 2}, _read_all(t.read(_path(self.PATH))))

        for success in [
            ("convert int key to string", {1: 0}, {"1": 0}),
            ("convert tuple value to list", {"": (1, 2)}, {"": [1, 2]}),
        ]:
            with self.subTest("should " + success[0]):
                testing = _memory_json()
                testing.write(_path(self.PATH), success[1])
                result = testing.read(_path(self.PATH))
                self.assertEqual(success[2], _read_all(result))

        with self.subTest("should fail for not serializable"):
            testing = _memory_json()
            with self.assertRaises(JsonAccessorError):
                # noinspection PyTypeChecker
                testing.write(_path(self.PATH), object)


class FilesystemJsonAccessorTest(TestCase):
    PATH: str = "path"

    def test_read(self) -> None:
        test_list: list[tuple[str, bytes, str, type[int | str], object]] = [
            ("fail if bad json", b"bad", self.PATH, int, JsonDecodeError),
            ("fail if not dict", b"[]", self.PATH, str, JsonDecodeError),
            ("fail if not exists", b"[]", "n", int, JsonReadError),
            ("fail if not list", b'{"1": 2}', self.PATH, int, JsonDecodeError),
            ("read dict", b'{"1": 2}', self.PATH, str, {"1": 2}),
            ("read list", b"[1, 2]", self.PATH, int, [1, 2]),
        ]

        for test in test_list:
            with self.subTest("should %s" % (test[0],)):
                testing = _filesystem_json(_fs({self.PATH: test[1]}))
                expected = test[4]
                if isinstance(expected, type) and issubclass(expected, Exception):
                    with self.assertRaises(expected):
                        testing.read(_path(test[2]), test[3])
                else:
                    result = testing.read(_path(test[2]), test[3])
                    self.assertEqual(expected, _read_all(result))

        with self.subTest("should fail if not a json"):
            t = _filesystem_json(fs=_fs({self.PATH: b"wrong"}))
            with self.assertRaises(JsonDecodeError):
                t.read(_path(self.PATH))

        with self.subTest("should fail if not an object"):
            t = _filesystem_json(fs=_fs({self.PATH: b"[]"}))
            with self.assertRaises(JsonDecodeError):
                t.read(_path(self.PATH), key_type=str)

        with self.subTest("should fail if not exists"):
            t = _filesystem_json(fs=_fs())
            with self.assertRaises(JsonReadError):
                t.read(_path(self.PATH))

        with self.subTest("should return object"):
            t = _filesystem_json(fs=_fs({self.PATH: b'{"a":1}'}))
            result = t.read(_path(self.PATH))
            self.assertEqual({"a": 1}, _read_all(result))

        with self.subTest("should fail for not committed"):
            fs = _fs()
            fs.create_folder(_path("not committed"))
            testing = _filesystem_json(fs)
            with self.assertRaises(JsonAccessorError):
                # noinspection PyTypeChecker
                testing.read(_path(self.PATH))

    def test_write(self) -> None:
        with self.subTest("should create json"):
            fs = _fs()
            t = _filesystem_json(fs=fs)
            t.write(_path(self.PATH), {"a": 1})
            fs.commit()
            result = b"".join(fs.load_file(_path(self.PATH)))
            self.assertEqual(b'{\n\t"a": 1\n}', result)

        with self.subTest("should fail for not serializable"):
            testing = _filesystem_json(fs=_fs())
            with self.assertRaises(JsonAccessorError):
                # noinspection PyTypeChecker
                testing.write(_path(self.PATH), object)
