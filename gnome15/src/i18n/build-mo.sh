#!/bin/bash

for i in *.po
do
   bn=$(basename $i .po)
   ll=$(basename ${bn} .en_GB).mo
   echo "${i} -> ${ll}"
   msgfmt ${i} --output-file en_GB/LC_MESSAGES/${ll}
done
