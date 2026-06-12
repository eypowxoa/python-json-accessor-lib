# JSON Accessor

Read and write JSON.

Usage:

```python
from atomic_filesystem_lib import MemoryFilesystem
from virtual_path_lib import VirtualPath

from json_accessor_lib import FilesystemJsonAccessor, JsonAccessorError

try:
    fs = MemoryFilesystem()
    path = VirtualPath('example.json')
    json = FilesystemJsonAccessor(fs)
    json.write(path, {'a': 42})
    fs.commit()
    data = json.read(path, str)
    print(data.extract_int('a')) # outputs 42
    json.read(VirtualPath('wrong'))
except JsonAccessorError as json_error:
    print(json_error.args[0]) # outputs error
```
