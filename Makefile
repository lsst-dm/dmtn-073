DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)
BRANCH = tickets/DM-12620
SCHEMA_URL = https://raw.githubusercontent.com/lsst/daf_butler/$(BRANCH)/config/registry/default_schema.yaml

TABLES = Dataset DatasetType DatasetTypeUnits DatasetTypeMetadata DatasetComposition DatasetCollection \
	Execution Run Quantum
COLUMNS = $(foreach tbl,$(TABLES),generated/$(tbl)_columns.tex)
GRAPHS = $(foreach tbl,$(TABLES),generated/$(tbl)_relationships.pdf)

$(DOCNAME).pdf: $(DOCNAME).tex $(COLUMNS) $(GRAPHS)
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error

generated/schema.yaml:
	curl $(SCHEMA_URL) > generated/schema.yaml

%_relationships.dot %_columns.tex: generated/schema.yaml generated/regen.py
	python generated/regen.py $*

%_relationships.pdf: %_relationships.dot
	dot -Tpdf $< > $@

generated: $(COLUMNS) $(GRAPHS)

clean:
	rm $(COLUMNS) $(GRAPHS)
	latexmk -C

.PHONY: clean generated
