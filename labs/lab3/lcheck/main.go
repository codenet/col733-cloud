package main

import (
	"bufio"
	"fmt"
	"os"
	"reflect"
	"regexp"
	"strconv"

	"github.com/anishathalye/porcupine"
)

type crInputOutput struct {
	op    bool
	key   string
	value string
}

type crState map[string]string

func cloneMap(m crState) crState {
	m2 := make(crState)
	for k, v := range m {
		m2[k] = v
	}
	return m2
}

var crModel = porcupine.Model{

	Init: func() interface{} {
		return make(crState)
	},

	Step: func(state, input, output interface{}) (bool, interface{}) {
		m := state.(crState)
		in := input.(crInputOutput)

		if in.op {
			// Put
			m2 := cloneMap(m)
			m2[in.key] = in.value
			return true, m2
		} else {
			// Get
			out := output.(crInputOutput)
			if val, ok := m[out.key]; ok {
				return val == out.value, state
			} else {
				// Initial default value is "0"
				return out.value == "0", state
			}
		}
	},

	Equal: func(state1, state2 interface{}) bool {
		return reflect.DeepEqual(state1, state2)
	},

	DescribeOperation: func(input, output interface{}) string {
		in := input.(crInputOutput)
		out := output.(crInputOutput)
		if in.op {
			return fmt.Sprintf("put(%v, %v)", in.key, in.value)
		} else {
			return fmt.Sprintf("get(%v) = %v", in.key, out.value)
		}
	},
}

func getWorkerId(matches []string) int {
	workerId, err := strconv.Atoi(matches[1])
	if err != nil {
		fmt.Println("Error parsing worker id: ", err)
		os.Exit(1)
	}
	return workerId
}

func parseLog(filename string) []porcupine.Event {
	// Read log file
	file, err := os.Open(filename)
	if err != nil {
		fmt.Println("Error opening file: ", err)
		os.Exit(1)
	}
	defer file.Close()

	// Parse log file
	var events []porcupine.Event

	// Regular expression to capture INFO level logs for setter and getter with key and value
	reSetter := regexp.MustCompile(`INFO\s+worker_(?P<worker_id>\d+)\s+Setting\s(?P<key>\w+)\s=\s(?P<value>\d+)`)
	reSetterSet := regexp.MustCompile(`INFO\s+worker_(?P<worker_id>\d+)\s+Set\s(?P<key>\w+)\s=\s(?P<value>\d+)`)
	reGetterGet := regexp.MustCompile(`INFO\s+worker_(?P<worker_id>\d+)\s+Get\s(?P<key>\w+)\s=\s(?P<value>\d+)`)
	reGetter := regexp.MustCompile(`INFO\s+worker_(?P<worker_id>\d+)\s+Getting\s(?P<key>\w+)`)

	id := 0
	procIdMap := make(map[int]int)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()

		switch {
		case reSetter.MatchString(line):
			matches := reSetter.FindStringSubmatch(line)
			workerId := getWorkerId(matches)
			events = append(events, porcupine.Event{ClientId: workerId, Kind: porcupine.CallEvent, Value: crInputOutput{true, matches[2], matches[3]}, Id: id})
			procIdMap[workerId] = id
			id++
		case reSetterSet.MatchString(line):
			matches := reSetterSet.FindStringSubmatch(line)
			workerId := getWorkerId(matches)
			events = append(events, porcupine.Event{ClientId: workerId, Kind: porcupine.ReturnEvent, Value: crInputOutput{true, matches[2], matches[3]}, Id: procIdMap[workerId]})
			delete(procIdMap, workerId)
		case reGetter.MatchString(line):
			matches := reGetter.FindStringSubmatch(line)
			workerId := getWorkerId(matches)
			events = append(events, porcupine.Event{ClientId: workerId, Kind: porcupine.CallEvent, Value: crInputOutput{false, matches[2], ""}, Id: id})
			procIdMap[workerId] = id
			id++
		case reGetterGet.MatchString(line):
			matches := reGetterGet.FindStringSubmatch(line)
			workerId := getWorkerId(matches)
			events = append(events, porcupine.Event{ClientId: workerId, Kind: porcupine.ReturnEvent, Value: crInputOutput{false, matches[2], matches[3]}, Id: procIdMap[workerId]})
			delete(procIdMap, workerId)
		}
	}

	return events
}

func checkLinearizability(filename string) bool {
	fmt.Println("Checking linearizability of log file: ", filename)

	events := parseLog(filename)
	// fmt.Println("Parsed events: ", events)
	if len(events) == 0 {
		fmt.Println("No events found in log file!")
		return false
	}

	passed := porcupine.CheckEvents(crModel, events)
	if passed {
		fmt.Println("Linearizability check passed!")
	} else {
		fmt.Println("Linearizability check failed!")
	}
	return passed
}

func main() {
	fmt.Println("Testing linearizability with Porcupine...")

	if len(os.Args) != 2 {
		fmt.Println("Usage: go run main.go <log-file-path>")
		os.Exit(1)
	}

	filename := os.Args[1]
	fmt.Println("Reading log file: ", filename)

	checkLinearizability(filename)

}
