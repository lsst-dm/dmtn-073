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
from collections import OrderedDict
from textwrap import TextWrapper

from lsst.utils import getPackageDir


# Load YAML files into OrderedDicts
def orderedYamlCtor(loader, node):
    return OrderedDict(loader.construct_pairs(node))

yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, orderedYamlCtor)


class ForeignKey:

    def __init__(self, node):
        self.sources = node['src'] if isinstance(node['src'], list) else [node['src']]
        targets = node['tgt'] if isinstance(node['tgt'], list) else [node['tgt']]
        # strip out tables, leaving just the fields
        self.targets = [t.split(".")[1] for t in targets]
        # extract exactly one table from the original targets
        try:
            self.table, = set(t.split(".")[0] for t in targets)
        except ValueError:
            raise ValueError("Foreign key target columns have no/different tables: %s" % targets)

    def sql(self):
        return "FOREIGN KEY ({sources}) REFERENCES {table} ({targets})".format(
            table=self.table, sources=", ".join(self.sources), targets=", ".join(self.targets)
        )


class TableFormatter:

    ESC_TRANS = str.maketrans(
        dict(
            [(c, '\\' + c) for c in '#$%&_{}'] +
            [('\\', '\\textbackslash{}'),
             ('^', '\\textasciicircum{}'),
             ('~', '\\textasciitilde{}')]
        )
    )

    def __init__(self, name, node):
        self.name = name
        self.node = node

    def run(self, stream):
        self.open(stream)
        self.columns(stream)
        self.foreignKeys(stream)
        self.close(stream)

    def open(self, stream):
        print(
            r"  \begin{tabular}{| l | l | l | p{0.5\textwidth} |}",
            r"    \hline",
            r"    \textbf{Name} & \textbf{Type} & \textbf{Attributes} & \textbf{Description} \\",
            r"    \hline",
            sep='\n',
            file=stream
        )

    def columns(self, stream):
        template = r"  {name} & {type} & {attributes} &"
        wrapper = TextWrapper(width=70, initial_indent='    ', subsequent_indent='    ')
        for column in self.node['columns']:
            if column.get("primary_key", False):
                attributes = "PRIMARY KEY"
            elif not column.get("nullable", True):
                attributes = "NOT NULL"
            else:
                attributes = ""
            print(template.format(name=column['name'].translate(self.ESC_TRANS),
                                  type=column['type'].translate(self.ESC_TRANS),
                                  attributes=attributes),
                  file=stream)
            print(*wrapper.wrap(column['doc'].translate(self.ESC_TRANS)), sep='\n', file=stream)
            print(r'    \\', file=stream)
            print(r'\hline', file=stream)

    def foreignKeys(self, stream):
        for node in self.node.get('foreignKeys', ()):
            text = ForeignKey(node).sql()
            print(r'  \multicolumn{4}{|l|}{%s} \\' % text.translate(self.ESC_TRANS), file=stream)
        print(r'\hline', file=stream)

    def close(self, stream):
        print(r"\end{tabular}", file=stream)


class GraphFormatter:

    def __init__(self, name, node):
        self.name = name
        self.node = node
        self.fKeys = [ForeignKey(n) for n in self.node.get("foreignKeys", ())]
        self.sources = [n['name'] for n in self.node.get("columns", ())]
        self.tables = OrderedDict()
        # Make unique lists of target fields participated in foreign keys and group
        # targets by table, keeping the original order as much as possible.
        for fKey in self.fKeys:
            if fKey.table not in self.tables:
                self.tables[fKey.table] = list(fKey.targets)
            else:
                for target in self.fKey.targets:
                    if target not in self.tables[fKey.table]:
                        self.tables[fKey.table].append(target)

    def vertex(self, stream, table, fields, rank=None):
        print('    {table} [label=<'.format(table=table), file=stream)
        print('      <table border="0" cellborder="1" cellpadding="6" cellspacing="0">', file=stream)
        print('        <tr><td><b>{table}</b></td></tr>'.format(table=table), file=stream)
        for field in fields:
            print('        <tr><td port="{field}">{field}</td></tr>'.format(field=field), file=stream)
        print('      </table>', file=stream)
        print('    >];', file=stream)

    def edges(self, stream, fKey):
        template = '  {name}:{source} -> {table}:{target} '
        '[dir="both" arrowtail="crowtee" arrowhead="nonetee"];'
        for source, target in zip(fKey.sources, fKey.targets):
            print(template.format(name=self.name, source=source, table=fKey.table, target=target),
                  file=stream)

    def run(self, stream):
        print('digraph {name}_relationships {{'.format(name=self.name), file=stream)
        print('  node [shape=plaintext, fontname=helvetica, fontsize=10]', file=stream)
        print('  rankdir=LR', file=stream)
        related = list(self.tables.items())
        even = related[::2]
        odd = related[1::2]
        print('  {', file=stream)
        print('    rank=min;', file=stream)
        for table, targets in even:
            self.vertex(stream, table, targets)
        print('  }', file=stream)
        print('  {', file=stream)
        print('    rank=same;', file=stream)
        self.vertex(stream, self.name, self.sources)
        print('  }', file=stream)
        print('  {', file=stream)
        print('    rank=max;', file=stream)
        for table, targets in odd:
            self.vertex(stream, table, targets)
        print('  }', file=stream)
        for fKey in self.fKeys:
            self.edges(stream, fKey)
        print('}', file=stream)


def formatStandardTable(name, tree):
    path, _ = os.path.split(__file__)
    node = tree["registry"]['schema']['tables'][name]
    tf = TableFormatter(name, node)
    with open(os.path.join(path, name + "_columns.tex"), 'w') as f:
        tf.run(f)
    gf = GraphFormatter(name, node)
    with open(os.path.join(path, name + "_relationships.dot"), 'w') as f:
        gf.run(f)


def processDataUnits(tree):
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
        for link in node['link']:
            dataset['columns'].append({
                'name': link['name'],
                'type': link['type'],
                'doc': 'DataUnit link; see %s.' % name,
            })


def main(path):
    with open(path, 'r') as f:
        tree = yaml.safe_load(f)
    processDataUnits(tree)
    formatStandardTable("Dataset", tree)


if __name__ == "__main__":
    main(os.path.join(getPackageDir("daf_butler"), "config", "registry", "default_schema.yaml"))
