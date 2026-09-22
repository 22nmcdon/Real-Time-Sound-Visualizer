"""Pull the page's script out into a file node can parse.

`scope.html` is one file on purpose, which makes `node --check` and the
non-browser unit tests awkward until the script is lifted out of it. The result
is build output, not source: tests/check.js is gitignored.
"""
import os, pathlib

HERE = os.path.dirname(os.path.abspath(__file__))
src = pathlib.Path(HERE, "scope.html").read_text()
i = src.index("<script>")
j = src.rindex("</script>")
out = pathlib.Path(HERE, "tests", "check.js")
out.write_text(src[i + 8:j])
print("wrote", out)
