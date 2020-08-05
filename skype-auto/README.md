#### OS: Ubuntu 18.04
#### Required Chrome Version: Version 76.0.3809.100 (Official Build) (64-bit)
#### Test
1. Setup two VMs with the required version of Chrome

2. Install python dependencies

3. Initialization: Open Chrome and login web.skype.com and create a meeting, with the credentials in agent.py

4. Run `python agent.py 0 0` to create a meeting and get the meeting URL

5. Start the receiver: Run `python agent.py 1 2 [URL]` in one VM to start audio recording

6. Start the sender: Run `python agent.py 0 1 [URL]` in another VM to play the example audio

7. Kill the receiver (CTRL+C) and play the output.wav file
