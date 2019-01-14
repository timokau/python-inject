"""
Tool that injects code into a python module at the first legal point.
That means after any shebangs, module docstrings and feature imports.
More precisely, code is injected immediately before the first statement
that is not a __future__ import. Only one statement gets injected, which
is a call to `exec` which can then execute an arbitrary python file. The
environment of that execution can be separated or not.
"""


import ast
import tokenize

def _is_future_import(node):
    return isinstance(node, ast.ImportFrom) and node.module == "__future__"

def _is_string(node):
    if hasattr(node, 'value'):
        node = node.value
    return isinstance(node, ast.Str)

class FindInjectionPointVisitor(ast.NodeVisitor):
    """
    A node-visitor that finds the first valid code injection point (i.e.
    immediately before the first non-__future__-import statement) and
    returns its position.
    """
    def generic_visit(self, node):
        if isinstance(node, ast.stmt) \
                and not _is_future_import(node) \
                and not _is_string(node):
            return (node.lineno, node.col_offset)

        for _, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        result = self.visit(item)
                        if result is not None:
                            return result
            elif isinstance(value, ast.AST):
                result = self.visit(value)
                if result is not None:
                    return result
        return None

def _generate_inject_str(file_to_exec, separate_env=True):
    """
    Generate the `exec` call to inject. The explicit `compile` is not
    strictly necessary but will link the code to a filename for nicer
    error messages.
    Passing an empty dict to `exec` will create a new separate
    environment, thus making sure the injected code cannot pollute the
    environment of the module. If that is not wanted, no dict is
    passed and the default is to share an environment.
    """

    extra_exec_args = ", dict()" if separate_env else ""
    inject = "exec(compile(open('{0}', 'rb').read(), '{0}', 'exec'){1});".format(
        file_to_exec,
        extra_exec_args,
    )
    return inject

def _find_inject_pos(source):
    """
    Return value may be None if no insert position was found.
    """
    tree = ast.parse(source)
    visitor = FindInjectionPointVisitor()
    result = visitor.visit(tree)
    return result

def _inject_bytes(source, to_inject, pos):
    lines = source.splitlines(True)
    if pos is not None:
        (line, col) = pos
        replace = lines[line - 1] # 0 indexing
        replace = replace[:col] + to_inject + replace[col:]
        lines[line - 1] = replace
    else:
        # no inject position found, inject at end
        lines += [to_inject + b'\n']
    return b''.join(lines)

def inject_exec(source, to_exec, encoding="utf-8", separate_env=True):
    """
    Injects an exec call to into a given source.
    """

    to_inject = _generate_inject_str(to_exec.replace("'", "\\'"), separate_env)
    pos = _find_inject_pos(source)
    return _inject_bytes(source, to_inject.encode(encoding), pos)

def inject_to_file(filename, to_exec, separate_env=True):
    """
    Injects an exec call into a python file.
    """

    with open(filename, 'rb') as source_file:
        (encoding, _) = tokenize.detect_encoding(source_file.readline)

    with open(filename, 'rb') as source_file:
        source = source_file.read()
        if len(source) == 0:
            # much less edge cases if the file always has at least one
            # line
            source += b'\n'

    new_source = inject_exec(source, to_exec, encoding, separate_env)
    with open(filename, 'wb') as target_file:
        target_file.write(new_source)

def _main():
    import argparse
    parser = argparse.ArgumentParser(description='Wrap python libraries')
    parser.add_argument('source_file', type=str, help='Python file to inject code into')
    parser.add_argument('inject_file', type=str, help='File with python code to inject')
    args = parser.parse_args()
    inject_to_file(args.source_file, args.inject_file)

if __name__ == "__main__":
    _main()
