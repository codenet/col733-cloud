package main

import (
	"os"
	"testing"
)

func TestMain(m *testing.M) {
	os.Exit(m.Run())
}

func TestLinearizable1(t *testing.T) {
	t.Log("test parse log")
	filename := "/Users/baadalvm/iitd/col733/craq/lcheck/lin1.log"
	status := checkLinearizability(filename)
	if status {
		t.Log("Linearizable")
	} else {
		t.Error("Not Linearizable")
	}
}

func TestNonLinearizable1(t *testing.T) {
	t.Log("test parse log")
	filename := "/Users/baadalvm/iitd/col733/craq/lcheck/non-lin1.log"
	status := checkLinearizability(filename)
	if status {
		t.Error("Linearizable")
	} else {
		t.Log("Not Linearizable")
	}
}
