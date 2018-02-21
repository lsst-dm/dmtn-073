DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)
BRANCH = tickets/DM-12620
SCHEMA_URL = https://raw.githubusercontent.com/lsst/daf_butler/$(BRANCH)/config/registry/default_schema.yaml

TABLES = generated/Dataset_columns.tex
GRAPHS = generated/Dataset_relationships.pdf

$(DOCNAME).pdf: $(DOCNAME).tex $(TABLES) $(GRAPHS)
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error

generated/schema.yaml:
	curl $(SCHEMA_URL) -o generated/schema.yaml

%_relationships.dot %_columns.tex: generated/schema.yaml generated/regen.py
	python generated/regen.py $*

%_relationships.pdf: %_relationships.dot
	dot -Tpdf $< > $@

generated: $(TABLES) $(GRAPHS)

clean:
	rm $(TABLES) $(GRAPHS)
	latexmk -C

.PHONY: clean generated
