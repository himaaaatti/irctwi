

.PHONY : test
test:
	python test/irctwi_test.py

.PHONY : run
run:
	python irctwi/irctwi.py
