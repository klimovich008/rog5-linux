#!/usr/bin/env python3
"""Reject module-level rebinding of controller functions/lambdas/imports.

This is a narrow composition check, not a proof of arbitrary Python behavior.
Run it on the complete assembled live controller before issuing a candidate.
Local variables inside functions are deliberately outside this check.
"""
import ast
from pathlib import Path
import sys


def names(target):
    if isinstance(target,ast.Name):return [target.id]
    if isinstance(target,(ast.Tuple,ast.List)):
        return [name for child in target.elts for name in names(child)]
    if isinstance(target,ast.Starred):return names(target.value)
    return []


class Bindings(ast.NodeVisitor):
    def __init__(self):self.protected={};self.writes=[]
    def protect(self,name,node):self.protected.setdefault(name,[]).append(node.lineno)
    def bind(self,target,node):self.writes.extend((name,node.lineno) for name in names(target))
    def visit_FunctionDef(self,node):self.protect(node.name,node)
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_ClassDef(self,node):self.protect(node.name,node)
    def visit_Lambda(self,node):pass
    def visit_Import(self,node):
        for alias in node.names:self.protect(alias.asname or alias.name.split('.')[0],node)
    def visit_ImportFrom(self,node):
        for alias in node.names:self.protect(alias.asname or alias.name,node)
    def visit_Assign(self,node):
        for target in node.targets:
            if isinstance(node.value,ast.Lambda):
                for name in names(target):self.protect(name,node)
            else:self.bind(target,node)
        self.visit(node.value)
    def visit_AnnAssign(self,node):
        self.bind(node.target,node)
        if node.value:self.visit(node.value)
    def visit_AugAssign(self,node):self.bind(node.target,node);self.visit(node.value)
    def visit_NamedExpr(self,node):self.bind(node.target,node);self.visit(node.value)
    def visit_For(self,node):self.bind(node.target,node);self.generic_visit(node)
    visit_AsyncFor=visit_For
    def visit_With(self,node):
        for item in node.items:
            if item.optional_vars:self.bind(item.optional_vars,node)
        self.generic_visit(node)
    visit_AsyncWith=visit_With
    def visit_ExceptHandler(self,node):
        if node.name:self.writes.append((node.name,node.lineno))
        self.generic_visit(node)


def conflicts(source):
    scope=Bindings();scope.visit(ast.parse(source))
    result=[f'{name}: protected at {scope.protected[name]}, rebound at line {line}'
            for name,line in scope.writes if name in scope.protected]
    result += [f'{name}: repeated protected definitions at {lines}'
               for name,lines in scope.protected.items() if len(lines)>1]
    return sorted(result)


if __name__=='__main__':
    if len(sys.argv)<2:raise SystemExit('usage: check-controller-bindings.py CONTROLLER...')
    failed=False
    for argument in sys.argv[1:]:
        path=Path(argument);found=conflicts(path.read_text())
        for problem in found:print(f'FAIL {path.name}: {problem}')
        failed |= bool(found)
    if failed:raise SystemExit(1)
    print('PASS complete controller module bindings remain distinct')
