package main

import (
	"testing"

)


func Test_anagram(t *testing.T) {
	type args struct {
		str string
	}

	tests := []struct {
		name string
		args args
		want bool
	}{
		// TODO: Add test cases.
		{
			name: " Case 1",
			args: args{
				str: "dbca",
			},
			want: false,
		},
		{
			name: " Case 2",
			args: args{
				str: "abcd",
			},
			want: true,
		},
		{
			name: " Case 3",
			args: args{
				str: "below",
			},
			want: false,
		},
		{
			name: " Case 4",
			args: args{
				str: "elbow",
			},
			want: true,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := anagram(tt.args.str); got != tt.want {
				t.Errorf("anagram() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestSortString(t *testing.T) {
	type args struct {
		w string
	}
	tests := []struct {
		name string
		args args
		want string
	}{
		{
			name: " Happy Case",
			args: args{
				w: "dcba",
			},
			want: "abcd",
		},	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := SortString(tt.args.w); got != tt.want {
				t.Errorf("SortString() = %v, want %v", got, tt.want)
			}
		})
	}
}