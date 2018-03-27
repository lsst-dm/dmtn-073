#!/usr/bin/env python
#
# LSST Data Management System

# Copyright 2018 AURA/LSST.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <https://www.lsstcorp.org/LegalNotices/>.
#

import yaml
import os
import sys
import re
from contextlib import contextmanager

from collections import OrderedDict, namedtuple
from textwrap import TextWrapper

GENERATED_PATH, _ = os.path.split(__file__)


# Load YAML files into OrderedDicts
def orderedYamlCtor(loader, node):
    return OrderedDict(loader.construct_pairs(node))

yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, orderedYamlCtor)


class Printer:

    ESCAPE_TRANSLATION_DICT = str.maketrans(
        dict(
            [(c, '\\' + c) for c in '#$%&_{}'] +
            [('\\', '\\textbackslash{}'),
             ('^', '\\textasciicircum{}'),
             ('~', '\\textasciitilde{}')]
        )
    )

    def __init__(self, stream, indent="", regexes=None):
        self.stream = stream
        self.indent = indent
        self.regexes = regexes if regexes is not None else dict()

    def direct(self, text=""):
        print(self.indent, text, sep="", file=self.stream)

    def format(self_, text, *args, **kwds):
        self_.direct(text.format(*args, **kwds))

    def escape(self, text):
        return text.translate(self.ESCAPE_TRANSLATION_DICT)

    def substitute(self, text):
        for regex, repl in self.regexes.items():
            text = regex.sub(repl, text)
        return text

    @contextmanager
    def block(self, begin, end, indent="  "):
        self.direct(begin)
        yield Printer(stream=self.stream, indent=self.indent+indent,
                      regexes=self.regexes)
        self.direct(end)


SourceTargetPair = namedtuple("SourceTargetPair", ["source", "target"])


class Table:
    __slots__ = ("name", "columns", "joins", "pKey")

    @classmethod
    def fromTree(cls, name, tableTree):
        columns = OrderedDict((c["name"], c) for c in tableTree['columns'])
        pKey = tuple(c["name"] for c in columns.values() if c.get("primary_key", False))
        return cls(name=name, columns=columns, pKey=pKey)

    def __init__(self, name, columns, pKey):
        self.name = name
        self.columns = columns
        self.joins = SourceTargetPair(source=[], target=[])
        self.pKey = pKey

    def __eq__(self, other):
        return self.name == other.name

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "TableVertex(name={self.name}, columns={self.columns})".format(self=self)

    def printColumns(self, printer):
        with printer.block(begin=r"\begin{tabular}{| l | l | l | p{0.5\textwidth} |}",
                           end=r"\end{tabular}") as p:
            p.direct(r"\hline")
            p.direct(r"\textbf{Name} & \textbf{Type} & \textbf{Attributes} & \textbf{Description} \\")
            p.direct(r"\hline")
            template = r"{name} & {type} & {attributes} &"
            wrapper = TextWrapper(width=70, initial_indent=p.indent+"  ", subsequent_indent=p.indent+"  ")
            for column in self.columns.values():
                if column.get("primary_key", False):
                    attributes = "PRIMARY KEY"
                elif not column.get("nullable", True):
                    attributes = "NOT NULL"
                else:
                    attributes = ""
                p.format(template, name=p.escape(column['name']), type=p.escape(column['type']),
                         attributes=attributes)
                for line in wrapper.wrap(p.substitute(p.escape(column['doc']))):
                    p.direct(line)
                p.direct(r'    \\')
                p.direct(r'\hline')

    def printGraphViz(self, printer, columns=None):
        printer.direct(self.name)
        with printer.block(begin='[label=<', end='>];') as p2:
            with p2.block(begin='<table border="0" cellborder="1" cellpadding="3" cellspacing="0">',
                          end='</table>') as p3:
                p3.format('<tr><td><b>{self.name}</b></td></tr>', self=self)
                skipped = []
                for name in self.columns.keys():
                    if columns is not None and name not in columns:
                        skipped.append(name)
                        continue
                    p3.format('<tr><td port="{name}">{name}</td></tr>', name=name)
                if len(skipped) == 1:
                    p3.format('<tr><td>{name}</td></tr>', name=skipped[0])
                elif len(skipped) > 1:
                    p3.direct('<tr><td>...</td></tr>')


class Port(namedtuple("Port", ["table", "columns", "many"])):
    __slots__ = ()

    def __str__(self):
        return self.table.name

    def __repr__(self):
        return "Port(name={self.table.name}, columns={self.columns})".format(self=self)

    @staticmethod
    def ensureList(tree):
        return list(tree) if isinstance(tree, list) else [tree]

    @classmethod
    def fromTreeSource(cls, fKeyTree, sourceTable):
        columns = cls.ensureList(fKeyTree['src'])
        # This is a one-to-one join iff the foreign key columns include all
        # primary key columns.
        many = not (sourceTable.pKey and set(sourceTable.pKey).issubset(columns))
        return cls(
            table=sourceTable,
            columns=columns,
            many=many
        )

    @classmethod
    def fromTreeTarget(cls, fKeyTree, allTables):
        columns = []
        tables = set()
        for t in cls.ensureList(fKeyTree['tgt']):
            table, column = t.split(".")
            columns.append(column)
            tables.add(table)
        assert len(tables) == 1, str(fKeyTree)
        return cls(
            table=allTables[tables.pop()],
            columns=columns,
            many=False
        )

    @property
    def arrow(self):
        """The GraphViz arrow head/tail type for this edge-vertex connection (`str`)."""
        return "crowtee" if self.many else "nonetee"


class Join(SourceTargetPair):
    __slots__ = ()

    @classmethod
    def fromTree(cls, fKeyTree, sourceTable, allTables):
        result = cls(
            source=Port.fromTreeSource(fKeyTree, sourceTable=sourceTable),
            target=Port.fromTreeTarget(fKeyTree, allTables=allTables),
        )
        result.source.table.joins.source.append(result)
        result.target.table.joins.target.append(result)
        return result

    def printGraphViz(self, printer, color=None):
        if color is not None:
            color = 'color={}'.format(color)
        else:
            color = ""
        template = (
            "{self.source.table.name}:{sourceCol} -> {self.target.table.name}:{targetCol} "
            "[arrowtail={self.source.arrow} arrowhead={self.target.arrow} {color}]"
        )
        for sourceCol, targetCol in zip(self.source.columns, self.target.columns):
            printer.format(template, color=color, self=self, sourceCol=sourceCol, targetCol=targetCol)


class SchemaGraph:

    def __init__(self):
        with open(os.path.join(GENERATED_PATH, "schema.yaml"), 'r') as f:
            tree = yaml.safe_load(f)
        # Add standard (non-DataUnit) tables.
        self.tables = OrderedDict()
        self.joins = []
        self.addTables(tree["tables"])
        # Process DataUnits recursively, so we can build up their joins to Dataset
        # and sort them topologically.
        todo = tree['dataUnits']
        self.units = OrderedDict()

        def recurse(unitName, unitTree):
            if unitTree is None:
                return
            unitTree['needed'] = set()

            deps = unitTree.get("dependencies", {})
            for req in deps.get("required", ()):
                recurse(req, todo.pop(req, None))
                unitTree['needed'] |= self.units[req]['needed']
            for opt in deps.get("optional", ()):
                recurse(opt, todo.pop(opt, None))

            unitTree['needed'] |= set(link['name'] for link in unitTree['link'])
            self.units[unitName] = unitTree

        while todo:
            recurse(*todo.popitem())

        # Walk through DataUnits, adding to self.tables, self.joins, and the
        # the Dataset table's columns.
        datasetTable = self.tables["Dataset"]
        extraTables = {}
        for unitName, unitTree in self.units.items():
            for tableName, tableTree in unitTree.get('tables', {}).items():
                if tableName == unitName:
                    thisTable = Table.fromTree(tableName, tableTree)
                    self.tables[tableName] = thisTable
                    joinColumns = [columnName for columnName in unitTree['needed']]
                    self.joins.append(
                        Join(target=Port(table=thisTable, columns=joinColumns,
                                         many=False),
                             source=Port(table=datasetTable,
                                         columns=list(joinColumns), many=True))
                    )
                    for fKeyTree in tableTree.get("foreignKeys", ()):
                        self.joins.append(
                            Join.fromTree(fKeyTree, sourceTable=thisTable,
                                          allTables=self.tables)
                        )
                else:
                    extraTables[tableName] = tableTree
            for link in unitTree['link']:
                datasetTable.columns[link['name']] = {
                    'name': link['name'],
                    'type': link['type'],
                    'doc': r'DataUnit link; see %s.' % unitName,
                }
        # Need to add extras at their end, because their foreign keys may
        # target other DataUnit tables that otherwise might not have been
        # added yet.
        self.addTables(extraTables)

        # Walk through DataUnitJoins, adding to self.tables, self.joins.
        self.unitJoins = tree["dataunit_joins"]
        for joinName, joinTree in tree["dataunit_joins"].items():
            tableTree = joinTree.get("tables", None)
            if tableTree:
                self.addTables(tableTree)


    def addTables(self, tree):
        # Add column descriptions.
        for tableName, tableTree in tree.items():
            self.tables[tableName] = Table.fromTree(tableName, tableTree)
        # Add standard (non-DataUnit) joins from foreignKey entries.
        for tableName, tableTree in tree.items():
            for fKeyTree in tableTree.get("foreignKeys", ()):
                self.joins.append(Join.fromTree(fKeyTree, sourceTable=self.tables[tableName],
                                                allTables=self.tables))

    def removeTables(self, toRemove):
        """Remove the given tables from the graph (including all joins involving them)."""
        for tableName in toRemove:
            del self.tables[tableName]

        def filterJoins(joins):
            return [join for join in joins
                    if join.source.table.name not in toRemove and join.target.table.name not in toRemove]

        for table in self.tables.values():
            table.joins.source[:] = filterJoins(table.joins.source)
            table.joins.target[:] = filterJoins(table.joins.target)
        self.joins[:] = filterJoins(self.joins)

    def getDataUnitTables(self):
        r = set()
        for unitTree in self.units.values():
            for tableName in unitTree.get('tables', {}).keys():
                r.add(tableName)
        return r

    def getProvenanceTables(self):
        return set(["Quantum", "Run", "Execution", "DatasetConsumers"])

    def getAllTables(self):
        return set(self.tables.keys())

    def makeRegExes(self):
        units = self.units.keys()
        tables = self.tables.keys() - units
        template = r"(?<!\w)({})(?!\w)"
        return {
            re.compile(template.format("|".join(units))): r"\\unitref{\1}",
            re.compile(template.format("|".join(tables))): r"\\tblref{\1}",
            re.compile(r'"(\w+)"'): r"``\1''"
        }

    def printGraphViz(self, printer):
        colors = ["lawngreen", "indigo", "magenta1", "orangered",
                  "lightskyblue3", "lightcoral", "mediumpurple", "forestgreen",
                  "royalblue", "firebrick1", "yellow4", "navyblue"]
        printer.direct('digraph relationships')
        with printer.block(begin='{', end='}') as p2:
            p2.direct('node [shape=plaintext fontname=helvetica fontsize=10]')
            p2.direct('edge [dir=both]')
            p2.direct('rankdir=LR')
            p2.direct('concentrate=true')
            for table in self.tables.values():
                table.printGraphViz(p2)
            for n, join in enumerate(self.joins):
                join.printGraphViz(p2, color=colors[n%len(colors)])

    def printDataUnit(self, name, printer):
        unitTree = self.units[name]
        printer.format(r"\subsubsection{{{name}}}", name=name)
        printer.format(r"\label{{unit:{name}}}", name=name)
        printer.direct()
        wrapper = TextWrapper(width=70, initial_indent=printer.indent, subsequent_indent=printer.indent)
        for line in wrapper.wrap(printer.substitute(printer.escape(unitTree['doc']))):
            printer.direct(line)
        printer.direct()
        deps = unitTree.get("dependencies", {})
        req = deps.get("required", None)
        if req is None:
            printer.direct(r"\textbf{Dependencies:} none")
        elif len(req) == 1:
            printer.format(r"\textbf{{Dependencies:}} {dep}", dep=printer.escape(req[0]))
        else:
            with printer.block(begin=r"\begin{itemize}", end=r"\end{itemize}") as p:
                for dep in req:
                    p.format(r"\item {dep}", dep=dep)
        printer.direct()
        values = unitTree["link"]
        printer.direct(r"\textbf{Value Fields:}")
        with printer.block(begin=r"\begin{itemize}", end=r"\end{itemize}") as p:
            for v in values:
                p.format(r"\item \textbf{{{name} ({type}):}}", name=p.escape(v['name']), type=p.escape(v['type']))
                doc = v.get("doc", None)
                if doc is None:
                    doc = self.tables[name].columns[v['name']]['doc']
                if doc is not None:
                    wrapper = TextWrapper(width=70, initial_indent=p.indent + "  ",
                                          subsequent_indent=p.indent + "  ")
                    for line in wrapper.wrap(p.escape(doc)):
                        p.direct(line)
        printer.direct()
        if 'tables' in unitTree:
            printer.format(r"\textbf{{Table:}} \hyperref[tbl:{name}]{{{name}}}", name=name)
            with printer.block(begin=r"\begin{table}[!htb]", end=r"\end{table}") as p:
                with p.block(begin=r"{\footnotesize", end=r"}") as p2:
                    self.tables[name].printColumns(p2)
                p.format(r"\caption{{{name} Columns}}", name=name)
                p.format(r"\label{{tbl:{name}}}", name=name)
        else:
            printer.direct(r"\textbf{Table:} none")

    def printDataUnitJoin(self, name, printer):
        tree = self.unitJoins[name]
        printer.format(r"\subsubsection{{{name}}}", name=name)
        printer.format(r"\label{{join:{name}}}", name=name)
        printer.direct()
        wrapper = TextWrapper(width=70, initial_indent=printer.indent, subsequent_indent=printer.indent)
        for line in wrapper.wrap(printer.substitute(printer.escape(tree['doc']))):
            printer.direct(line)
        printer.direct()
        if 'tables' in tree:
            if 'sql' in tree:
                printer.format(r"\textbf{{View:}} \hyperref[tbl:{name}]{{{name}}}, defined as:", name=name)
                with printer.block(begin=r"\begin{verbatim}", end=r"\end{verbatim}") as p:
                    p.direct(tree['sql'])
            else:
                printer.format(r"\textbf{{Table:}} \hyperref[tbl:{name}]{{{name}}}", name=name)
            with printer.block(begin=r"\begin{table}[!htb]", end=r"\end{table}") as p:
                with p.block(begin=r"{\footnotesize", end=r"}") as p2:
                    self.tables[name].printColumns(p2)
                p.format(r"\caption{{{name} Columns}}", name=name)
                p.format(r"\label{{tbl:{name}}}", name=name)
        elif 'sql' in tree:
            printer.direct(r"\textbf{Join Expression:}")
            printer.direct()

            def fmtSide(x):
                return printer.substitute(", ".join(x) if isinstance(x, list) else x)

            printer.format(r"For \texttt{{lhs}}={lhs} and \texttt{{rhs}}={rhs},",
                           lhs=fmtSide(tree['lhs']),
                           rhs=fmtSide(tree['rhs']))
            with printer.block(begin=r"\begin{verbatim}", end=r"\end{verbatim}") as p:
                    p.direct(tree['sql'])


if __name__ == "__main__":
    provenanceTables = set(["Quantum", "Run", "Execution", "DatasetConsumers"])
    graph = SchemaGraph()
    _, output = os.path.split(sys.argv[1])
    with open(os.path.join(GENERATED_PATH, output), 'w') as f:
        printer = Printer(stream=f, regexes=graph.makeRegExes())
        if output.endswith("_columns.tex"):
            table, _ = output.split("_")
            graph.tables[table].printColumns(printer)
        elif output.endswith("_unit.tex"):
            unit, _ = output.split("_")
            graph.printDataUnit(unit, printer)
        elif output.endswith("_join.tex"):
            join, _ = output.split("_")
            graph.printDataUnitJoin(join, printer)
        elif output == "relationships.dot":
            graph.printGraphViz(printer)
        else:
            raise ValueError("Unrecognized output file")
