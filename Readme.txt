- Using Raspberry Pi Imager make a bootable SD image for Pi
- Boot and configure Pi with prompts
- Clock raspberry icon at the top left of the desktop -> Preferences -> Raspberry Pi Configuration
- Select tab Interfaces and enable SSH and Serial Port
- In terminal:
- cd .. (This should change folder to /home)
- sudo mkdir root
- sudo chown pi:pi root
- cd root
- copy the pi4 files to root (i.e.: * main_loop_config_30bins_slim.py  pi@192.168.1.127:/home/root/)
    quick copy and paste stuff for development:
    scp main_loop_config_30bins_slim.py  pi@192.168.1.127:/home/root/
    scp ser.py  pi@192.168.1.127:/home/root/
- sudo chmod 755 *      (Changes everything in /home/root to runnable among other things)
Install dependencies
- sudo pip3 install socketio
- sudo pip3 install python-socketio


Put the files in /home/root	(make this dir if not there)
sudo chown prae:prae /home/root	(or whatever current user's name is instead of prae)
pip3 install -r requirements.txt

Make rc.local executable:
sudo chown root /etc/rc.local
sudo chmod 755 /etc/rc.local
Execute:
sudo /etc/init.d/rc.local start