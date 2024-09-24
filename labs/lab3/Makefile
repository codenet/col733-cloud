# SHELL := /bin/bash

# Set the starting port and bandwidth
START_PORT ?= 9900
BANDWIDTH ?= 100kbps
NUM_PORTS ?= 4

.PHONY: limit_ports clean

# Define the command to limit bandwidth using tc for a given port
define tc_limit_bandwidth
	sudo tc qdisc add dev lo root handle 1: htb default 10 || true
	sudo tc class add dev lo parent 1: classid 1:$(1) htb rate $(BANDWIDTH) ceil $(BANDWIDTH)
	sudo tc filter add dev lo protocol ip parent 1:0 prio 1 u32 match ip dport $(1) 0xffff flowid 1:$(1)
	sudo tc qdisc add dev lo handle ffff: ingress || true
	sudo tc filter add dev lo parent ffff: protocol ip u32 match ip sport $(1) 0xffff police rate $(BANDWIDTH) burst 10k drop
endef

# Apply bandwidth limit for 4 consecutive ports starting from START_PORT
limit_ports:
	$(call tc_limit_bandwidth,$(START_PORT))
	$(call tc_limit_bandwidth,$(shell expr $(START_PORT) + 1))
	$(call tc_limit_bandwidth,$(shell expr $(START_PORT) + 2))
	$(call tc_limit_bandwidth,$(shell expr $(START_PORT) + 3))

# Clean up the tc rules
clean_tc:
	sudo tc qdisc del dev lo root || true
	sudo tc qdisc del dev lo handle ffff: ingress || true


setup: clean_tc limit_ports
	export PYTHONPATH=.

cr: setup
	python3 -m unittest cr.cr_test.TestCR.test_gen_history

craq: setup
	python3 -m unittest craq.craq_test.TestCRAQ.test_gen_history
