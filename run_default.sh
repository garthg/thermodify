max=72
min=69


cd `dirname $0`
while true; do
    python3 run_one_update.py $max $min 2>&1 | tee -a log.txt
    sleep 300
done
