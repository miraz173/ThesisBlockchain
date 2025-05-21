curl "http://127.0.0.1:6003/mine"
sleep 2
curl "http://127.0.0.1:6001/nodes/resolve"
sleep 1
curl "http://127.0.0.1:6002/nodes/resolve"
sleep 3
curl "http://127.0.0.1:6003/nodes/resolve"
sleep 2
curl "http://127.0.0.1:6002/mine"
curl "http://127.0.0.1:6003/nodes/resolve"
sleep 1
curl "http://127.0.0.1:6003/mine"
curl "http://127.0.0.1:6001/mine"

# python voter.py --voter 14 --candidate "Candidate X"
# python voter.py --voter 17 --candidate "Candidate X" 
# python voter.py --voter 16 --candidate "Candidate Y" 
# python voter.py --voter 18 --candidate "Candidate X"
# python voter.py --voter 15 --candidate "Candidate A"