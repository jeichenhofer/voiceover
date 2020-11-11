import os
import time
import subprocess

def audio_setup():
	cmd = """
	pacmd load-module module-null-sink sink_name=skype;
	pacmd update-sink-proplist skype device.description=skype;
	pacmd update-source-proplist skype.monitor device.description=skype_monitor;
	pacmd set-default-sink skype;
	pacmd set-default-source skype.monitor
	"""
	ret = os.popen(cmd).read()
	# print (ret)

	cmd = "pacmd list-sinks|awk '/index:/ {printf $0} /name:/ {print $0};' | grep 'skype' | awk -F ' ' '{print $3}'"
	sink_id = os.popen(cmd).read().strip("\n")
	# print ("sink_id", sink_id)

	cmd = "pacmd list-sink-inputs|awk '/index:/ {printf $0} /client:/ {print $0};' | grep 'Chromium' | awk -F ' ' '{print $2}'"
	sink_input_id = os.popen(cmd).read().strip("\n")
	# print ("sink_input_id", sink_input_id)

	cmd = "pacmd move-sink-input %s %s" % (sink_input_id, sink_id)
	# print (cmd)
	os.popen(cmd)


	cmd = "pacmd list-sources|awk '/index:/ {printf $0} /name:/ {print $0};' | grep 'skype.monitor' | awk -F ' ' '{print $3}'"
	# print (cmd)
	source_id = os.popen(cmd).read().strip("\n")
	# print ("source_id", source_id)

	cmd = "pacmd list-source-outputs|awk '/index:/ {printf $0} /client:/ {print $0};' | grep 'Chrome input' | awk -F ' ' '{print $2}'"
	# print (cmd)
	source_output_id = os.popen(cmd).read().strip("\n")
	# print ("source_output_id", source_output_id)

	cmd = "pacmd move-source-output %s %s" % (source_output_id, source_id)
	# print (cmd)
	os.popen(cmd)
	
def player_setup(app_name):
	cmd = "pacmd list-sinks|awk '/index:/ {printf $0} /name:/ {print $0};' | grep 'skype' | awk -F ' ' '{print $3}'"
	sink_id = os.popen(cmd).read().strip("\n")
	# print ("sink_id", sink_id)

	cmd = "pacmd list-sink-inputs|awk '/index:/ {printf $0} /client:/ {print $0};' | grep '%s' | awk -F ' ' '{print $2}'" % app_name
	sink_input_id = os.popen(cmd).read().strip("\n")
	# print ("sink_input_id", sink_input_id)

	cmd = "pacmd move-sink-input %s %s" % (sink_input_id, sink_id)
	os.popen(cmd)

def recorder_setup(app_name):
	cmd = "pacmd list-sources|awk '/index:/ {printf $0} /name:/ {print $0};' | grep 'skype.monitor' | awk -F ' ' '{print $3}'"
	# print (cmd)
	source_id = os.popen(cmd).read().strip("\n")
	# print ("source_id", source_id)

	# time.sleep(3)
	cmd = "pacmd list-source-outputs|awk '/index:/ {printf $0} /client:/ {print $0};' | grep '%s' | awk -F ' ' '{print $2}'" % app_name
	# print (cmd)
	source_output_id = os.popen(cmd).read().strip("\n")
	# print ("source_output_id", source_output_id)

	cmd = "pacmd move-source-output %s %s" % (source_output_id, source_id)
	# print (cmd)
	# os.popen(cmd)
	r = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE, universal_newlines=True)
	out, err = r.communicate()


def audio_cleanup():
	cmd = """
	pacmd unload-module module-null-sink
	pacmd unload-module module-null-source
	pacmd unload-module module-loopback
	"""

	ret = os.popen(cmd).read()
	# print (ret)
	

if __name__ == '__main__':
	audio_cleanup()
