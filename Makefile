DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)

TABLES = generated/Dataset_columns.tex

GRAPHS = generated/Dataset_relationships.pdf

# For Travis CI build: doesn't declare dependencies on generated inputs,
# since Travis can't build them anyway.
$(DOCNAME).pdf: $(DOCNAME).tex
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error

# Remaining targets are for locals builds, and require daf_butler to be setup
# and graphviz to be installed.  Run "make full" to make everything with
# proper dependency management.
regen:
	python generated/regen.py

%_relationships.pdf: %_relationships.dot
	dot -Tpdf $< > $@

generated: regen $(TABLES) $(GRAPHS)

full: generated $(DOCNAME).tex
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error

clean:
	rm $(TABLES) $(GRAPHS)
	latexmk -C
