# XReality

**A Unity environment for turning any real-life robot into a VR-controlled mech!**
This was made as a proof-of-concept framework for future immersive VR interactions within Unity.

Made by **Alan Alcocer-Iturriza** and **Omar Khan** for the CPSC584 Human-Robot Interaction course at the University of Calgary.

A special thanks to our professor **Dr. Ehud Sharlin** and our Teacher Assistant **Matt Newton**.

Watch our demo video below!

[![Watch the video on YouTube](https://i9.ytimg.com/vi/1RQFDsQtsAc/mqdefault.jpg?sqp=CJS1lMEG-oaymwEmCMACELQB8quKqQMa8AEB-AH-CYAC0AWKAgwIABABGDwgVShyMA8=&rs=AOn4CLDbEV5LygCGvDZNqL7a2Fk29l_31g)](https://youtu.be/1RQFDsQtsAc)



## Default PiCrawler Setup

### Computer Setup
1. Download [Unity Hub](https://unity.com/download)
2. On Unity Hub, download Unity version 6000.0.28f1
3. Clone this repository with `git clone https://github.com/AlanAyy/CPSC584-XReality/`
4. Open this project in Unity
5. Connect to the same Wifi network as the robot
6. Run it!

### Raspberry Pi Setup
This project was made to work with the [SunFounder PiCrawler](https://docs.sunfounder.com/projects/pi-crawler/en/latest/)
1. Install the Raspberry Pi OS using the [SunFounder guide](https://docs.sunfounder.com/projects/pi-crawler/en/latest/python/python_start/installing_the_os.html)
2. Upload the code from the CrawlerCode folder onto the Raspberry Pi
3. Connect to the same Wifi network as the computer
4. Run the code!



## Custom Robot Setup
To run this on other robots, you would need to change:
1. The commands send by the buttons in the Unity project
2. The Python code ran by your robot
