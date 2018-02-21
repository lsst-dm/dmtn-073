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

    def __init__(self, stream, indent=""):
        self.stream = stream
        self.indent = indent

    def direct(self, text):
        print(self.indent, text, sep="", file=self.stream)

    def format(self_, text, *args, **kwds):
        self_.direct(text.format(*args, **kwds))

    def insert(self, text, *args):
        self.direct(text % args)

    def escape(self, text):
        return text.translate(self.ESCAPE_TRANSLATION_DICT)

    @contextmanager
    def block(self, begin, end, indent="  "):
        self.direct(begin)
        yield Printer(stream=self.stream, indent=self.indent+indent)
        self.direct(end)


SourceTargetPair = namedtuple("SourceTargetPair", ["source", "target"])


class TableVertex:
    __slots__ = ("name", "columns", "links")

    def __init__(self, name, columns, links):
        self.name = name
        self.columns = columns
        self.links = links

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

    def writeAll(self):
        with open(os.path.join(GENERATED_PATH, self.name + "_columns.tex"), 'w') as f:
            self.printColumns(Printer(stream=f))
        with open(os.path.join(GENERATED_PATH, self.name + "_relationships.dot"), 'w') as f:
            self.printRelationships(Printer(stream=f))

    def printColumns(self, printer, doForeignKeys=False):
        with printer.block(begin=r"\begin{tabular}{| l | l | l | p{0.5\textwidth} |}",
                           end=r"\end{tabular}") as p:
            p.direct(r"\hline")
            p.direct(r"\textbf{Name} & \textbf{Type} & \textbf{Attributes} & \textbf{Description} \\")
            p.direct(r"\hline")
            template = r"{name} & {type} & {attributes} &"
            wrapper = TextWrapper(width=70, initial_indent=p.indent+"  ", subsequent_indent=p.indent+"  ")
            for column in self.columns:
                if column.get("primary_key", False):
                    attributes = "PRIMARY KEY"
                elif not column.get("nullable", True):
                    attributes = "NOT NULL"
                else:
                    attributes = ""
                p.format(template, name=p.escape(column['name']), type=p.escape(column['type']),
                         attributes=attributes)
                for line in wrapper.wrap(p.escape(column['doc'])):
                    p.direct(line)
                p.direct(r'    \\')
                p.direct(r'\hline')
            if doForeignKeys:
                for link in self.links.source:
                    p.insert(r'  \multicolumn{4}{|l|}{%s} \\', p.escape(link.sql))
            p.direct(r'\hline')

    def printRelationships(self, printer):
        # Make a dict of {<table>: <list-of-columns>} for any tables related
        # to the focus table, and containing just the columns that participate
        # in those relationships.
        related = OrderedDict()
        for edge in self.links.source:
            assert edge.source.table is self
            related.setdefault(edge.target.table, set()).update(edge.target.columns)
        for edge in self.links.target:
            assert edge.target.table is self
            related.setdefault(edge.source.table, set()).update(edge.source.columns)
        # We'll now turn the dict into a list of tuples so we can slice it;
        # even entries will go on the left and odd on the right, with the
        # node for self in the middle (those layout/rank hints make the layout
        # graphviz produces much better).
        related = list(related.items())
        even = related[::2]
        odd = related[1::2]

        colors = ["red", "green", "blue", "cyan", "magenta"]

        printer.format('digraph {name}_relationships', name=self.name)
        with printer.block(begin='{', end='}') as p2:
            p2.direct('node [shape=plaintext, fontname=helvetica, fontsize=10]')
            p2.direct('rankdir=LR')
            with p2.block(begin="{", end="}") as p3:
                p3.direct('rank=min;')
                for table, columns in even:
                    table.printGraphVizVertex(p3, columns=columns)
            with p2.block(begin="{", end="}") as p3:
                p3.direct('rank=same;')
                self.printGraphVizVertex(p3)
            with p2.block(begin="{", end="}") as p3:
                p3.direct('rank=max;')
                for table, columns in odd:
                    table.printGraphVizVertex(p3, columns=columns)
            for n, link in enumerate(self.links.source):
                link.printGraphVizEdge(p2, color=colors[n%len(colors)])
            for n, link in enumerate(self.links.target):
                link.printGraphVizEdge(p2, color=colors[n%len(colors)])

    def printGraphVizVertex(self, printer, columns=None):
        printer.direct(self.name)
        with printer.block(begin='[label=<', end='>];') as p2:
            with p2.block(begin='<table border="0" cellborder="1" cellpadding="6" cellspacing="0">',
                          end='</table>') as p3:
                p3.format('<tr><td><b>{self.name}</b></td></tr>', self=self)
                for column in self.columns:   # use self.columns to set order, as columns arg may be a set
                    if columns is not None and column['name'] not in columns:
                        continue
                    p3.format('<tr><td port="{field}">{field}</td></tr>', field=column['name'])


class LinkPort(namedtuple("LinkPort", ["table", "columns", "many"])):
    __slots__ = ()

    def __str__(self):
        return self.table.name

    def __repr__(self):
        return "LinkPort(name={self.table.name}, columns={self.columns})".format(self=self)

    @classmethod
    def fromForeignKeySource(cls, fKeyNode, sourceTable):
        return cls(
            table=sourceTable,
            columns=fKeyNode['src'] if isinstance(fKeyNode['src'], list) else [fKeyNode['src']],
            many=fKeyNode.get('many', True)
        )

    @classmethod
    def fromForeignKeyTarget(cls, fKeyNode, vertices):
        columns = []
        tables = set()
        if isinstance(fKeyNode['tgt'], list):
            for t in fKeyNode['tgt']:
                table, column = t.split(".")
                columns.append(column)
                tables.add(table)
        else:
            table, column = fKeyNode['tgt'].split(".")
            columns.append(column)
            tables.add(table)
        assert len(tables) == 1, str(fKeyNode)
        return cls(
            table=vertices[tables.pop()],
            columns=columns,
            many=False
        )

    @property
    def arrow(self):
        """The GraphViz arrow head/tail type for this edge-vertex connection (`str`)."""
        return "crowtee" if self.many else "nonetee"


class LinkEdge(SourceTargetPair):
    __slots__ = ()

    @classmethod
    def fromForeignKey(cls, fKeyNode, sourceTable, vertices):
        result = cls(
            source=LinkPort.fromForeignKeySource(fKeyNode, sourceTable=sourceTable),
            target=LinkPort.fromForeignKeyTarget(fKeyNode, vertices=vertices),
        )
        result.source.table.links.source.append(result)
        result.target.table.links.target.append(result)
        return result

    @property
    def sql(self):
        return "FOREIGN KEY ({srcColumns}) REFERENCES {targetTable} ({targetColumns})".format(
            targetTable=self.target.table.name,
            sourceColumns=", ".join(self.source.columns),
            targetColumns=", ".join(self.target.columns),
        )

    def printGraphVizEdge(self, printer, color=None):
        if color is not None:
            color = 'color="{}"'.format(color)
        else:
            color = ""
        template = (
            "{self.source.table.name}:{source} -> {self.target.table.name}:{target} "
            "[arrowtail={self.source.arrow} arrowhead={self.target.arrow} dir=both {color}]"
        )
        for source, target in zip(self.source.columns, self.target.columns):
            printer.format(template, self=self, source=source, target=target, color=color)


class SchemaGraph:

    @classmethod
    def fromTree(cls, tree):
        vertices = OrderedDict()
        # Add all tables (vertices)...
        for name, node in tree["registry"]["schema"]["tables"].items():
            vertices[name] = TableVertex(name=name, columns=list(node['columns']),
                                         links=SourceTargetPair(source=[], target=[]))
        # ...before adding any links (edges), since those need the table instances to exist.
        edges = []
        for name, node in tree["registry"]["schema"]["tables"].items():
            for fKeyNode in node.get("foreignKeys", ()):
                edges.append(LinkEdge.fromForeignKey(fKeyNode, sourceTable=vertices[name],
                                                     vertices=vertices))
        return cls(vertices=vertices, edges=edges)

    def __init__(self, vertices, edges):
        self.vertices = vertices
        self.edges = edges


def preprocessDataUnits(tree):
    dataset = tree['registry']['schema']['tables']['Dataset']
    done = OrderedDict()
    todo = tree['registry']['schema']['dataUnits']

    # Recurse to sort by dependencies and get recurvive "needed" links
    # for Dataset's foreign key constraints.
    def recurse(name, node):
        if node is None:
            return
        node['needed'] = []

        deps = node.get("dependencies", {})
        for req in deps.get("required", ()):
            recurse(req, todo.pop(req, None))
            node['needed'].extend(done[req]['needed'])
        for opt in deps.get("optional", ()):
            recurse(opt, todo.pop(opt, None))

        node['needed'].extend(node['link'])
        done[name] = node

    while todo:
        recurse(*todo.popitem())

    for name, node in done.items():
        if 'tables' in node:
            foreignKey = {
                'src': [],
                'tgt': []
            }
            try:
                table, = node['tables'].keys()
            except ValueError:
                raise ValueError("DataUnits may only have one table.")
            for link in node['needed']:
                if link['name'] not in foreignKey['src']:
                    foreignKey['src'].append(link['name'])
                    foreignKey['tgt'].append("%s.%s" % (table, link['name']))
            dataset['foreignKeys'].append(foreignKey)
            # Add DataUnit table to the main list of tables
            tree['registry']['schema']['tables'][table] = node['tables'][table]
        for link in node['link']:
            dataset['columns'].append({
                'name': link['name'],
                'type': link['type'],
                'doc': 'DataUnit link; see %s.' % name,
            })


def main(table):
    with open(os.path.join(GENERATED_PATH, "schema.yaml"), 'r') as f:
        tree = yaml.safe_load(f)
    preprocessDataUnits(tree)
    graph = SchemaGraph.fromTree(tree)
    graph.vertices[table].writeAll()

if __name__ == "__main__":
    _, table = os.path.split(sys.argv[1])
    main(table)
