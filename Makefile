DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)
BRANCH = tickets/DM-12620
SCHEMA_URL = https://raw.githubusercontent.com/lsst/daf_butler/$(BRANCH)/config/schema.yaml

TABLES = Dataset DatasetType DatasetTypeUnits DatasetTypeMetadata DatasetComposition DatasetCollection \
	Execution Run Quantum DatasetStorage VisitSensorRegion
COLUMNS = $(foreach tbl,$(TABLES),generated/$(tbl)_columns.tex)
UNITS = AbstractFilter Label SkyPix Camera Sensor PhysicalFilter Exposure Visit ExposureRange \
	SkyMap Tract Patch
UNIT_INCS = $(foreach unit,$(UNITS),generated/$(unit)_unit.tex)
JOINS = ExposureRangeJoin MultiCameraExposureJoin VisitSensorSkyPixJoin VisitSkyPixJoin PatchSkyPixJoin \
	TractSkyPixJoin VisitSensorPatchJoin VisitSensorTractJoin VisitPatchJoin VisitTractJoin
JOIN_INCS = $(foreach join,$(JOINS),generated/$(join)_join.tex)
GRAPHS = generated/relationships-all.pdf DataUnitJoins.pdf DataUnitJoinsLegend.pdf \
	generated/relationships-dataunits-only.pdf generated/relationships-no-dataunits.pdf

$(DOCNAME).pdf: $(DOCNAME).tex $(COLUMNS) $(GRAPHS) $(UNIT_INCS) $(JOIN_INCS)
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error -interaction=nonstopmode -file-line-error -synctex=1

generated/schema.yaml:
	curl $(SCHEMA_URL) > generated/schema.yaml

%_columns.tex: generated/schema.yaml generated/regen.py
	python generated/regen.py $@

%_unit.tex: generated/schema.yaml generated/regen.py
	python generated/regen.py $@

%_join.tex: generated/schema.yaml generated/regen.py
	python generated/regen.py $@

generated/relationships-%.dot: generated/schema.yaml generated/regen.py
	python generated/regen.py $@

generated/relationships-%.pdf: generated/relationships-%.dot
	dot -Tpdf $< > $@

DataUnitJoins.pdf: DataUnitJoins.dot
	dot -Tpdf $< > $@

DataUnitJoinsLegend.pdf: DataUnitJoinsLegend.dot
	dot -Tpdf $< > $@

generated: $(COLUMNS) $(GRAPHS) $(UNIT_INCS) $(JOIN_INCS)

clean:
	rm $(COLUMNS) $(GRAPHS) $(UNIT_INCS) $(JOIN_INCS)
	latexmk -C

.PHONY: clean generated
