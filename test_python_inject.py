import pytest
from python_inject import inject_exec

@pytest.mark.parametrize("example_file", [
    "test_examples/empty.py",
    "test_examples/multi_future_import.py",
    "test_examples/no_trailing_newline.py",
    "test_examples/one_line.py",
    "test_examples/only_docstring.py",
    "test_examples/only_future.py",
    "test_examples/regular.py",
])
def test_example(example_file):
    source = open(example_file).read()
    if source[-2:] == '@\n':
        # special case when @ means "last line"
        plain = source[:-2]
    else:
        plain = source.replace('@', '')

    target = source.replace('@', "exec(compile(open('INJECT', 'rb').read(), 'INJECT', 'exec'), dict());")
    result = inject_exec(plain, "INJECT")
    assert result == target
