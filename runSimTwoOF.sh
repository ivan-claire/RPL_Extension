#!/bin/bash
echo "Bash version ${BASH_VERSION}..."
printf "Link_Quality\Objective_Function\tOF0\tMRHOF\n" >> output.csv

# Run simulation for OF0
perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.5, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.0, \'rssi\' : -30\}/g" ./OrignalSimulator/SimEngine/Connectivity.py
for percent in {0..9..1}
do
  printf "$((percent+1))0\t\t\n" >> output.csv
  if [ $percent -lt 9 ]
  then
    perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$percent, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$((percent+1)), \'rssi\' : -30\}/g" ./OrignalSimulator/SimEngine/Connectivity.py
  else
    perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$percent, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 1.00, \'rssi\' : -30\}/g" ./OrignalSimulator/SimEngine/Connectivity.py
  fi
  echo "Objective Function: OF0, percent: $((percent+1))"
  cd ./OrignalSimulator/bin/
  python runSim.py
  cd ..
  cd ..
  file="./OrignalSimulator/bin/pdr_value/mean_pdr.txt"
  pdr=$(cat "$file")
  echo "pdr value of OF0, link quality $((percent+1))0 %: $pdr"
  awk -v value=$pdr -v row=$((percent+2)) -v col=2 'BEGIN{FS=OFS="\t"} NR==row {$col=value}1' output.csv > new.csv
  mv new.csv output.csv
done
if [ $percent -lt 9 ]
then
  perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$((percent+1)), \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.5, \'rssi\' : -30\}/g" ./OrignalSimulator/SimEngine/Connectivity.py
else
  perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 1.00, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.5, \'rssi\' : -30\}/g" ./OrignalSimulator/SimEngine/Connectivity.py
fi

# Run simulation for MRHOF
perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.5, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.0, \'rssi\' : -30\}/g" ./MrHofSimulators/SimEngine/Connectivity.py
for percent1 in {0..9..1}
do
  if [ $percent1 -lt 9 ]
  then
    perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$percent1, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$((percent1+1)), \'rssi\' : -30\}/g" ./MrHofSimulators/SimEngine/Connectivity.py
  else
    perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$percent1, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 1.00, \'rssi\' : -30\}/g" ./MrHofSimulators/SimEngine/Connectivity.py
  fi
  echo "Objective Function: MRHOF, percent: $((percent1+1))"
  cd ./MrHofSimulators/bin/
  python runSim.py
  cd ..
  cd ..
  file1="./MrHofSimulators/bin/pdr_value/mean_pdr.txt"
  pdr1=$(cat "$file1")
  echo "pdr value of MRHOF, link quality $((percent1+1))0 %: $pdr1"
  awk -v value=$pdr1 -v row=$((percent1+2)) -v col=3 'BEGIN{FS=OFS="\t"} NR==row {$col=value}1' output.csv > new.csv
  mv new.csv output.csv
done
if [ $percent1 -lt 9 ]
then
  perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.$((percent1+1)), \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.5, \'rssi\' : -30\}/g" ./MrHofSimulators/SimEngine/Connectivity.py
else
  perl -p -i -e "s/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 1.00, \'rssi\' : -30\}/CONNECTIVITY_MATRIX_LINK_QUALITY = \{\'pdr\' : 0.5, \'rssi\' : -30\}/g" ./MrHofSimulators/SimEngine/Connectivity.py
fi
echo ""
echo "Simulation Results"
cat output.csv
