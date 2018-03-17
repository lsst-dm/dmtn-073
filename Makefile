DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)
BRANCH = tickets/DM-12620
SCHEMA_URL = https://raw.githubusercontent.com/lsst/daf_butler/$(BRANCH)/config/registry/default_schema.yaml

TABLES = Dataset DatasetType DatasetTypeUnits DatasetTypeMetadata DatasetComposition DatasetCollection \
	Execution Run Quantum DatasetStorage
COLUMNS = $(foreach tbl,$(TABLES),generated/$(tbl)_columns.tex)
UNITS = AbstractFilter Label SkyPix Camera Sensor PhysicalFilter Exposure Visit ExposureRange SkyMap Tract Patch
UNIT_INCS = $(foreach unit,$(UNITS),generated/$(unit)_unit.tex)
GRAPHS = generated/All_relationships.pdf DataUnitJoins.pdf

$(DOCNAME).pdf: $(DOCNAME).tex $(COLUMNS) $(GRAPHS) $(UNIT_INCS)
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error

generated/schema.yaml:
	curl $(SCHEMA_URL) > generated/schema.yaml

%_columns.tex: generated/schema.yaml generated/regen.py
	python generated/regen.py $@

%_unit.tex: generated/schema.yaml generated/regen.py
	python generated/regen.py $@

%_relationships.dot: generated/schema.yaml generated/regen.py
	python generated/regen.py $@

%_relationships.pdf: %_relationships.dot
	dot -Tpdf $< > $@

DataUnitJoins.pdf: DataUnitJoins.dot
	dot -Tpdf $< > $@

generated: $(COLUMNS) $(GRAPHS) $(UNIT_INCS)

clean:
	rm $(COLUMNS) $(GRAPHS) $(UNIT_INCS)
	latexmk -C

.PHONY: clean generated
