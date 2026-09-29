#!/bin/sh
# ddrdiff.sh before after : per-frequency count and seconds delta
paste "$1" "$2" | awk -F'\t' '{split($1,a,/[ :\t]+/); } {n=split($0,f,"\t"); }
 /Freq/ {split($0,x,"\t"); name=x[1]; sub(/.*Freq /,"",name); sub(/:.*/,"",name); c1=x[3]; c2=x[7]; d1=x[4]; d2=x[8]; sub(/.*:/,"",c1); sub(/.*:/,"",c2); sub(/.*:/,"",d1); sub(/.*:/,"",d2); if (c2-c1 || d2-d1) printf "%s +%d %.1fs\n", name, c2-c1, (d2-d1)/19200000}
 /LPM/ {split($0,x,"\t"); c1=x[2]; c2=x[5]; sub(/.*:/,"",c1); sub(/.*:/,"",c2); if (c2-c1) print "LPM", x[1], "+" c2-c1}'
