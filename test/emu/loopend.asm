; DO/DOR loops whose last instruction is two words long (test/LoopEndCheck.java).
; loopend.words is this file assembled by asl, with the DOR extension word corrected to the
; displacement LA - PC = 4 (asl writes the absolute LA, see GHIDRA-RARE.md).
	cpu	56300
	org	$100
	do	#3,end1
	add	#$010000,a
end1:
	nop
	org	$110
	dor	#3,end2
	nop
	move	x:$1234,x0
end2:
	nop
	org	$120
	do	#3,end3
	nop
end3:
	nop
