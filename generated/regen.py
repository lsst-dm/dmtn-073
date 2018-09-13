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

import os
import re
import copy
from contextlib import contextmanager
from textwrap import TextWrapper

from lsst.daf.butler import Schema, SchemaConfig, DataUnitRegistry, DataUnitConfig
from lsst.daf.butler.core.utils import iterable

GENERATED_PATH, _ = os.path.split(__file__)


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


def printTableColumns(printer, table):
    """Print a LaTeX table description of the columns of a
    `sqlalchemy.schema.Table` object.

    Parameters
    ----------
    printer : `Printer`
        Object that handles formatting, special-character escaping, and the
        output file.
    table : `sqlalchemy.schema.Table`
        Table to describe.
    """
    with printer.block(begin=r"\begin{tabular}{| l | l | l | p{0.5\textwidth} |}",
                       end=r"\end{tabular}") as p:
        p.direct(r"\hline")
        p.direct(r"\textbf{Name} & \textbf{Type} & \textbf{Attributes} & \textbf{Description} \\")
        p.direct(r"\hline")
        template = r"{name} & {type} & {attributes} &"
        wrapper = TextWrapper(width=70, initial_indent=p.indent+"  ", subsequent_indent=p.indent+"  ")
        for column in table.columns.values():
            if column.primary_key:
                attributes = "PRIMARY KEY"
            elif not column.nullable:
                attributes = "NOT NULL"
            else:
                attributes = ""
            p.format(template, name=p.escape(column.name), type=p.escape(column.type.python_type.__name__),
                     attributes=attributes)
            if column.comment is not None:
                for line in wrapper.wrap(p.substitute(p.escape(column.comment))):
                    p.direct(line)
            p.direct(r'    \\')
            p.direct(r'\hline')


def printTableGraphNode(printer, table, columns=None):
    """Print a GraphViz node for a `sqlalchemy.schema.Table` object.

    Parameters
    ----------
    printer : `Printer`
        Object that handles formatting, special-character escaping, and the
        output file.
    table : `sqlalchemy.schema.Table`
        Table to describe.
    columns : sequence of `str`, optional
        A list of column names to include in the node.  If `None`, all columns
        will be included.
    """
    printer.direct(table.name)
    with printer.block(begin='[label=<', end='>];') as p2:
        with p2.block(begin='<table border="0" cellborder="1" cellpadding="3" cellspacing="0">',
                      end='</table>') as p3:
            p3.format('<tr><td><b>{table.name}</b></td></tr>', table=table)
            skipped = []
            for name in table.columns.keys():
                if columns is not None and name not in columns:
                    skipped.append(name)
                    continue
                p3.format('<tr><td port="{name}">{name}</td></tr>', name=name)
            if len(skipped) == 1:
                p3.format('<tr><td>{name}</td></tr>', name=skipped[0])
            elif len(skipped) > 1:
                p3.direct('<tr><td>...</td></tr>')


def printForeignKeyGraphEdge(printer, constraint, color=None):
    """Print a GraphViz edge for a `sqlalchemy.schema.ForeignKeyConstraint`
    object.

    Parameters
    ----------
    printer : `Printer`
        Object that handles formatting, special-character escaping, and the
        output file.
    constraint : `sqlalchemy.schema.ForeignKeyConstraint`
        Table to describe.
    color : `str`
        Color for graph edge (X11 name).
    """
    if color is not None:
        color = 'color={}'.format(color)
    else:
        color = ""
    fkNamesLocal = frozenset(c.name for c in constraint)
    pkNamesLocal = frozenset(c.name for c in constraint.table.primary_key)
    fkNamesRemote = frozenset(fk.column.name for fk in constraint.elements)
    pkNamesRemote = frozenset(c.name for c in constraint.referred_table.primary_key)

    def getArrow(pkNames, fkNames):
        if pkNames.issubset(fkNames):
            return "nonetee"
        else:
            return "crowtee"

    template = (
        "{constraint.table.name}:{local.name} -> {constraint.referred_table.name}:{remote.name} "
        "[arrowtail={arrowLocal} arrowhead={arrowRemote} {color}]"
    )
    for local, fk in zip(constraint.columns, constraint.elements):
        remote = fk.column
        printer.format(template, constraint=constraint, local=local, remote=remote,
                       arrowLocal=getArrow(pkNamesLocal, fkNamesLocal),
                       arrowRemote=getArrow(pkNamesRemote, fkNamesRemote),
                       color=color)


def printSchemaGraph(printer, schema):
    """Print a GraphViz edge for a `sqlalchemy.schema.ForeignKeyConstraint`
    object.

    Parameters
    ----------
    printer : `Printer`
        Object that handles formatting, special-character escaping, and the
        output file.
    schema : `lsst.daf.butler.Schema`
        Description of the Registry SQL schema.
    """
    colors = ["lawngreen", "indigo", "magenta1", "orangered",
              "lightskyblue3", "lightcoral", "mediumpurple", "forestgreen",
              "royalblue", "firebrick1", "yellow4", "navyblue"]
    printer.direct('digraph relationships')
    with printer.block(begin='{', end='}') as p2:
        p2.direct('node [shape=plaintext fontname=helvetica fontsize=10]')
        p2.direct('edge [dir=both]')
        p2.direct('rankdir=LR')
        p2.direct('concentrate=false')
        tablesSorted = sorted(schema.tables.values(), key=lambda t: t.name)
        for table in tablesSorted:
            printTableGraphNode(p2, table)
        n = 0
        for table in tablesSorted:
            for constraint in sorted(table.foreign_key_constraints, key=lambda fk: str(fk.elements)):
                printForeignKeyGraphEdge(p2, constraint, color=colors[n % len(colors)])
                n += 1


def printDataUnitDimension(printer, dimension, schema):
    """Print a LaTeX description section for a DataUnit dimension.

    Parameters
    ----------
    printer : `Printer`
        Object that handles formatting, special-character escaping, and the
        output file.
    dimension : `lsst.daf.butler.DataUnit`
        DataUnit dimension instance to describe.
    schema : `lsst.daf.butler.Schema`
        Description of the Registry SQL schema.
    """
    printer.format(r"\subsubsection{{{name}}}", name=dimension.name)
    printer.format(r"\label{{unit:{name}}}", name=dimension.name)
    printer.direct()
    wrapper = TextWrapper(width=70, initial_indent=printer.indent, subsequent_indent=printer.indent)
    for line in wrapper.wrap(printer.substitute(printer.escape(dimension.doc))):
        printer.direct(line)
    printer.direct()
    if not dimension.requiredDependencies:
        printer.direct(r"\textbf{Dependencies:} none")
    elif len(dimension.requiredDependencies) == 1:
        dep, = dimension.requiredDependencies
        printer.format(r"\textbf{{Dependencies:}} {dep}", dep=printer.escape(dep.name))
    else:
        with printer.block(begin=r"\begin{itemize}", end=r"\end{itemize}") as p:
            for dep in dimension.requiredDependencies:
                p.format(r"\item {dep}", dep=printer.escape(dep.name))
    printer.direct()
    printer.direct(r"\textbf{Value Fields:}")
    table = schema.tables.get(dimension.name, None)
    with printer.block(begin=r"\begin{itemize}", end=r"\end{itemize}") as p:
        for linkName in dimension.link:
            linkColumn = schema.tables["Dataset"].c[linkName]
            linkType = linkColumn.type.python_type.__name__
            p.format(r"\item \textbf{{{name} ({type}):}}", name=p.escape(linkName), type=p.escape(linkType))
            linkDoc = linkColumn.comment
            if linkDoc is None and table is not None:
                linkDoc = table.c[linkName].comment
            if linkDoc is not None:
                wrapper = TextWrapper(width=70, initial_indent=p.indent + "  ",
                                      subsequent_indent=p.indent + "  ")
                for line in wrapper.wrap(p.escape(linkDoc)):
                    p.direct(line)
    printer.direct()
    if table is not None:
        printer.format(r"\textbf{{Table:}} \hyperref[tbl:{name}]{{{name}}}", name=dimension.name)
        with printer.block(begin=r"\begin{table}[!htb]", end=r"\end{table}") as p:
            with p.block(begin=r"{\footnotesize", end=r"}") as p2:
                printTableColumns(p2, table)
            p.format(r"\caption{{{name} Columns}}", name=dimension.name)
            p.format(r"\label{{tbl:{name}}}", name=dimension.name)
    else:
        printer.direct(r"\textbf{Table:} none")


def printDataUnitJoin(printer, join, schema):
    """Print a LaTeX description section for a DataUnit join.

    Parameters
    ----------
    printer : `Printer`
        Object that handles formatting, special-character escaping, and the
        output file.
    join : `lsst.daf.butler.DataUnitJoin`
        DataUnit join instance to describe.
    schema : `lsst.daf.butler.Schema`
        Description of the Registry SQL schema.
    """
    printer.format(r"\subsubsection{{{name}}}", name=join.name)
    printer.format(r"\label{{join:{name}}}", name=join.name)
    printer.direct()
    wrapper = TextWrapper(width=70, initial_indent=printer.indent, subsequent_indent=printer.indent)
    for line in wrapper.wrap(printer.substitute(printer.escape(join.doc))):
        printer.direct(line)
    printer.direct()
    table = schema.tables.get(join.name, None)
    if table is not None:
        if join.name in schema.views:
            printer.format(r"\textbf{{View:}} \hyperref[tbl:{name}]{{{name}}}, defined as:", name=join.name)
            with printer.block(begin=r"\begin{verbatim}", end=r"\end{verbatim}") as p:
                p.direct(table.info["sql"])
        else:
            printer.format(r"\textbf{{Table:}} \hyperref[tbl:{name}]{{{name}}}", name=join.name)
        with printer.block(begin=r"\begin{table}[!htb]", end=r"\end{table}") as p:
            with p.block(begin=r"{\footnotesize", end=r"}") as p2:
                printTableColumns(p2, table)
            p.format(r"\caption{{{name} Columns}}", name=join.name)
            p.format(r"\label{{tbl:{name}}}", name=join.name)


def makeLinkRegularExpressions(schema, dataUnits):
    """Make substitution regular expressions for a Printer that create links
    and fix quotes.
    """
    units = set(dataUnits.keys())
    tables = schema.tables.keys() - units
    template = r"(?<!\w)({})(?!\w)"
    return {
        # If we see a DataUnit name, replace it with a hyperref macro to that section.
        re.compile(template.format("|".join(units))): r"\\unitref{\1}",
        # If we see a table name, replace it with a hyperref macro to that figure.
        re.compile(template.format("|".join(tables))): r"\\tblref{\1}",
        # If we see double-quoted text, replace it with directional LaTeX-friendly quotes.
        re.compile(r'"(\w+)"'): r"``\1''",
    }


def materializeAllViews(config):
    """Modify a SchemaConfig by setting all "materialize" options to True.
    """
    result = copy.deepcopy(config)
    for name in config.names():
        if name.endswith("materialize"):
            result[name] = True
    return result


def keepOnly(config, toKeep):
    """Modify a SchemaConfig by dropping all tables not in the given list
    """
    result = copy.deepcopy(config)
    for name, description in config["tables"].items():
        if name not in toKeep:
            del result["tables", name]
        else:
            fks = []
            for fk in description.get("foreignKeys", ()):
                tgt = tuple(iterable(fk.get("tgt")))
                table, _ = tgt[0].split(".")
                if table in toKeep:
                    fks.append(fk)
            result["tables", name, "foreignKeys"] = fks
    return result


if __name__ == "__main__":
    defaultSchema = Schema()
    materializedViewsConfig = materializeAllViews(SchemaConfig())
    noViewSchema = Schema(materializedViewsConfig)
    limitedSchema = Schema(materializedViewsConfig, limited=True)
    dataUnits = DataUnitRegistry.fromConfig(DataUnitConfig())
    dataUnitsOnlyConfig = keepOnly(materializedViewsConfig, ["Dataset"] + list(dataUnits.keys()))
    dataUnitsOnlySchema = Schema(dataUnitsOnlyConfig)
    regexes = makeLinkRegularExpressions(defaultSchema, dataUnits)

    for name, table in limitedSchema.tables.items():
        with open(os.path.join(GENERATED_PATH, f"{name}_columns.tex"), 'w') as f:
            printer = Printer(stream=f, regexes=regexes)
            printTableColumns(printer, table)

    for dimension in dataUnits.values():
        with open(os.path.join(GENERATED_PATH, f"{dimension.name}_unit.tex"), 'w') as f:
            printer = Printer(stream=f, regexes=regexes)
            printDataUnitDimension(printer, dimension, defaultSchema)

    for join in dataUnits.joins.values():
        with open(os.path.join(GENERATED_PATH, f"{join.name}_join.tex"), 'w') as f:
            printer = Printer(stream=f, regexes=regexes)
            printDataUnitJoin(printer, join, defaultSchema)

    with open(os.path.join(GENERATED_PATH, "relationships-limited.dot"), 'w') as f:
        printer = Printer(stream=f, regexes=regexes)
        printSchemaGraph(printer, limitedSchema)

    with open(os.path.join(GENERATED_PATH, "relationships-dataUnitsOnly.dot"), 'w') as f:
        printer = Printer(stream=f, regexes=regexes)
        printSchemaGraph(printer, dataUnitsOnlySchema)
