DOCTYPE = DMTN
DOCNUMBER = 073
DOCNAME = $(DOCTYPE)-$(DOCNUMBER)

$(DOCNAME).pdf: $(DOCNAME).tex
	latexmk -bibtex -xelatex $(DOCNAME) -halt-on-error

clean:
	latexmk -C
