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
import sys
import os
from collections import OrderedDict
from textwrap import TextWrapper

from lsst.utils import getPackageDir

TABLE_WIDTHS = OrderedDict([("name", 20), ("type", 8), ("attributes", 11), ("doc", 52)])
TABLE_ROW = "| " + " | ".join("{%s: <%d}" % p for p in TABLE_WIDTHS.items()) + " |\n"
TABLE_BORDER = "+-" + "-+-".join("-" * width for width in TABLE_WIDTHS.values()) + "-+\n"
TABLE_HEAD = "+=" + "=+=".join("=" * width for width in TABLE_WIDTHS.values()) + "=+\n"
MERGED_WIDTH = sum(TABLE_WIDTHS.values()) + (len(TABLE_WIDTHS) - 1)*3
MERGED_ROW = "| " + ("{text: <%d}" % MERGED_WIDTH) + " |\n"


# Load YAML files into OrderedDicts
def orderedYamlCtor(loader, node):
    return OrderedDict(loader.construct_pairs(node))

yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, orderedYamlCtor)


class TableFormatter:

    ESC_TRANS = str.maketrans(
        dict(
             [(c, '\\' + c) for c in '#S%&_{}'] +
             [('\\', '\\textbackslash{}'),
              ('^', '\\textasciicircum{}'),
              ('~', '\\textasciitilde{}')]
        )
    )

    def __init__(self, node):
        self.node = node

    def run(self, stream):
        self.open(stream)
        self.columns(stream)
        self.close(stream)

    def open(self, stream):
        print(
            r"\begin{tabular}{| l | l | l | p{0.4\textwidth} |}",
            r"  \hline",
            r"  Name & Type & Attributes & Description \\",
            r"  \hline",
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

    def close(self, stream):
        print(r"\end{tabular}", file=stream)


def formatHeader(stream):
    stream.write(TABLE_BORDER)
    stream.write(TABLE_ROW.format(name="Name", type="Type", attributes="Attributes",
                                  doc="Description"))
    stream.write(TABLE_HEAD)


def formatColumns(stream, node):
    wrapper = TextWrapper(width=TABLE_WIDTHS["doc"]-2)
    for column in node['columns']:
        doc = wrapper.wrap(column['doc'])
        if column.get("primary_key", False):
            attributes = "PRIMARY KEY"
        elif not column.get("nullable", True):
            attributes = "NOT NULL"
        else:
            attributes = ""
        assert(len(column['name']) <= TABLE_WIDTHS['name'])
        assert(len(column['type']) <= TABLE_WIDTHS['type'])
        assert(len(attributes) <= TABLE_WIDTHS['attributes'])
        stream.write(TABLE_ROW.format(name=column['name'], type=column['type'],
                                      attributes=attributes, doc="| " + doc[0]))
        for line in doc[1:]:
            stream.write(TABLE_ROW.format(name="", type="", attributes="", doc="| " + line))
        stream.write(TABLE_BORDER)


def formatForeignKeys(stream, node):
    wrapper = TextWrapper(width=MERGED_WIDTH, subsequent_indent="        ")
    for fKey in node.get('foreignKeys', ()):
        src = fKey['src']
        tgt = fKey['tgt']
        if not isinstance(src, list):
            src = [src]
        if not isinstance(tgt, list):
            tgt = [tgt]
        try:
            table, = set(t.split(".")[0] for t in tgt)
        except ValueError:
            raise ValueError("Foreign key target columns have no/different tables: %s" % tgt)
        src = ", ".join(src)
        tgt = ", ".join(t.split(".")[1] for t in tgt)
        text = "FOREIGN KEY ({src}) REFERENCES {table} ({src})".format(src=src, table=table, tgt=tgt)
        for line in wrapper.wrap(text):
            stream.write(MERGED_ROW.format(text=line))
        stream.write(TABLE_BORDER)
    stream.write(TABLE_BORDER)


def formatStandardTable(name, tree):
    path, _ = os.path.split(__file__)
    node = tree["registry"]['schema']['tables'][name]
    formatter = TableFormatter(node)
    with open(os.path.join(path, name + "_columns.tex"), 'w') as f:
        formatter.run(f)


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
