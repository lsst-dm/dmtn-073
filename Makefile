DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)
BRANCH = master

TABLES = Dataset DatasetType DatasetTypeUnits DatasetTypeMetadata DatasetComposition DatasetCollection \
	Execution Run Quantum DatasetStorage VisitSensorRegion
COLUMNS = $(foreach tbl,$(TABLES),generated/$(tbl)_columns.tex)
UNITS = AbstractFilter Label SkyPix Camera Sensor PhysicalFilter Exposure Visit ExposureRange \
	SkyMap Tract Patch
UNIT_INCS = $(foreach unit,$(UNITS),generated/$(unit)_unit.tex)
JOINS = ExposureRangeJoin MultiCameraExposureJoin VisitSensorSkyPixJoin VisitSkyPixJoin PatchSkyPixJoin \
	TractSkyPixJoin VisitSensorPatchJoin VisitSensorTractJoin VisitPatchJoin VisitTractJoin
JOIN_INCS = $(foreach join,$(JOINS),generated/$(join)_join.tex)
GRAPHS = generated/relationships-all.pdf generated/relationships-limited.pdf \
	generated/relationships-dataUnitsOnly.pdf \
	DataUnitJoins.pdf DataUnitJoinsLegend.pdf

$(DOCNAME).pdf: $(DOCNAME).tex $(COLUMNS) $(GRAPHS) $(UNIT_INCS) $(JOIN_INCS)
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error -interaction=nonstopmode -file-line-error -synctex=1

%_columns.tex: generated/regen.py
	python generated/regen.py $@

%_unit.tex: generated/regen.py
	python generated/regen.py $@

%_join.tex: generated/regen.py
	python generated/regen.py $@

generated/relationships-%.dot: generated/regen.py
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
