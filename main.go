package main


import (
	"fmt"
	"sort"
	"strings"
)

func main() {
	fmt.Println(anagram("elbow")) // this should be false
	fmt.Println(anagram("hello")) // this should be false
	fmt.Println(anagram("below")) // this should be true
	fmt.Println(anagram("hello")) // this should be true
	fmt.Println(anagram("grab")) // this should be false
	fmt.Println(anagram("elloh")) // this should be true
	fmt.Println(anagram("brag")) // this should be true
}

var m = make(map[string]int)
func SortString(w string) string {
	s := strings.Split(w, "")
	sort.Strings(s)
	return strings.Join(s, "")
}

func anagram (str string) bool {
	str = SortString(str)
	if _ , ok := m[str] ; ok {
		return true
	} else {
		m[str] = 0
	}
	return  false
}
