from selenium import webdriver
import chromedriver_binary
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import numpy as np
import time
import os
from selenium.webdriver.common.action_chains import ActionChains
import trans
import audioctr
import sys

# username and password
CREDS = {
	"c": {
		"user": "voiceoverclient@outlook.com",
		"pwd": "12345678@PU"
	},
	"s": {
		"user": "voiceoverserver@outlook.com",
		"pwd": "12345678@PU"
	}
}

CHROMEPATH = "/home/parallels/.config/google-chrome"

class VoiceoverAgent(object):
	"""docstring for VoiceoverAgent"""
	def __init__(self, user, pwd, chrome_path):
		self.user = user
		self.pwd = pwd
		self.chrome_path = chrome_path
		self.driver = self.init_browser()
		
	def init_browser(self):
		options = webdriver.ChromeOptions()
		options.add_argument(r"user-data-dir=%s" % self.chrome_path)
		options.add_argument("--window-size=200,600")
		driver = webdriver.Chrome(options=options)
		driver.set_window_position(0, 0)
		return driver

	def close(self):
		self.driver.close()

	def login(self):
		self.driver.get("https://web.skype.com/")
		time.sleep(5)
		print ("Login")
		if self.driver.current_url.startswith("https://login.live.com/"):
			print ("Input user name")
			elem = self.driver.find_element_by_name("loginfmt")
			elem.clear()
			elem.send_keys(self.user)
			elem.send_keys(Keys.RETURN)
			time.sleep(5)
			print ("Input user password")
			elem = self.driver.find_element_by_name("passwd")
			elem.clear()
			elem.send_keys(self.pwd)
			elem.send_keys(Keys.RETURN)
			time.sleep(10)

	def create_meeting(self):
		print ("Create meeting")
		self.driver.find_element_by_xpath('//*[@aria-label="Meet Now"]').click()
		time.sleep(10)
		self.driver.find_element_by_xpath('//*[@aria-label="Copy Link"]').click()
		cmd = "xsel --clipboard"
		r = os.popen(cmd)
		meeting_url = r.read().strip("\n")
		print ("Meeting URL:", meeting_url)
		return meeting_url

	def create_meeting_and_join(self):
		meeting_url = self.create_meeting()
		self.driver.find_element_by_xpath('//*[@title="Start Meeting"]').click()
		time.sleep(1)
		try:
			self.driver.find_element_by_xpath('//*[@aria-label="Microphone"]').click()
			time.sleep(1)
			self.driver.find_element_by_xpath('//*[@title="Start call"]').click()
		except:
			pass
		return meeting_url
		

	def join_meeting_by_url(self, URL):
		print ("Join meeting")
		self.driver.get(URL)
		time.sleep(5)
		if self.driver.current_url.startswith("https://join.skype.com/"):
			actions = ActionChains(self.driver)
			actions.send_keys(Keys.RETURN)
			actions.perform()
			time.sleep(5)

			""" for some cases these are reqiured
			# actions.send_keys("Leo")
			# actions.send_keys(Keys.RETURN)
			# actions.perform()
			"""
			
			print ("Turn on microphone")
			time.sleep(5)
			try:
				self.driver.find_element_by_xpath('//*[@aria-label="Microphone"]').click()
				time.sleep(1)
			except:
				try:
					self.driver.find_element_by_xpath('//*[@aria-label="Microphone, Off"]').click()
				except Exception as e:
					# print (str(e))
					pass
			time.sleep(1)

			try:
				self.driver.find_element_by_xpath('//*[@title="Start Meeting"]').click()
			except:
				try:
					self.driver.find_element_by_xpath('//*[@title="Join Meeting"]').click()
				except:
					self.driver.find_element_by_xpath('//*[@title="Join call"]').click()
			# actions.send_keys(Keys.RETURN)
			# actions.perform()




if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser()

	parser.add_argument('-t', choices=['c', 's'], help='Specify agent type: client (c) or server(s)')
	parser.add_argument('-a', choices=['create', 'play', 'record'], help='Specify action')
	parser.add_argument('-u', help='Meeting URL')
	parser.add_argument('-f', help='Audio file')


	args = parser.parse_args(sys.argv[1:])
	peer_id = args.t
	op = args.a
	url = args.u
	fin = args.f
	
	audioctr.audio_cleanup()
	agent = VoiceoverAgent(CREDS[peer_id]["user"], CREDS[peer_id]["pwd"], CHROMEPATH)
	agent.login()

	if op == "create":
		
		url = agent.create_meeting()
	else:
		assert url
		agent.join_meeting_by_url(url)
		
		
		# wait for initializing audio input/output
		time.sleep(5) 
	
		print ("Set up audio channels")
		# redirect input/output of chrome, wait for finishing setup
		audioctr.audio_setup()
		time.sleep(5)

		if op == "play":
			# may need this:
			# audioctr.player_setup("ALSA plug-in")
			print ("Play")
			trans.play_wav()

		if op == "record":
			# redirect input of the recording app
			audioctr.recorder_setup("ALSA plug-in")
			time.sleep(5)

			print ("Record")
			trans.record_wav()

		audioctr.audio_cleanup()

	print ("Exit...")
	agent.close()
