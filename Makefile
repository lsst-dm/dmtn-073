DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)

TABLES = generated/Dataset_columns.tex

GRAPHS = generated/Dataset_relationships.pdf

$(DOCNAME).pdf: $(DOCNAME).tex $(TABLES) $(GRAPHS)
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error

regen:
	python generated/regen.py

%_relationships.pdf: %_relationships.dot
	dot -Tpdf $< > $@

clean:
	rm $(TABLES) $(GRAPHS)
	latexmk -C
