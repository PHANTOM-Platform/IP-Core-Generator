#!/usr/bin/env python3

import os, sys, glob, subprocess, json, time, shutil, errno
import settings, repository
import websocket
from xml.dom import expatbuilder
from repository import ANSI_RED, ANSI_GREEN, ANSI_YELLOW, ANSI_BLUE, ANSI_MAGENTA, ANSI_CYAN, ANSI_END


tempdir = "_tmp/"
repository_ipcoregen_source = "ipcoregenerator"

#TODO get source files and directories from component network
srcfilesdir = 'src/'


def main():

	#Empty the temp dir
	if os.path.isdir(tempdir):
		shutil.rmtree(tempdir)
	os.mkdir(tempdir)


	# Usage
	if len(sys.argv) < 2:
		print("Usage: {} [mode] <args for mode>".format(sys.argv[0]))
		print("Valid modes are: subscribe, remote, local, upload, download, verify, listdeps")
		sys.exit(1)


	# Subscribe
	elif sys.argv[1] == 'subscribe':
		"""
		Subscribe to a project using the Application Manager. Waits for updates to the project and
		analyses any checked deployments continually.
		Arguments:
			[2] - project name to subscribe to
		"""
		if len(sys.argv) < 3:
			print("Usage: {} subscribe <model name>".format(sys.argv[0]))
			sys.exit(1)
		
		repository.set_project(sys.argv[2])
		repository.set_source(settings.repository_user_dir)
		subscribe(sys.argv[2], settings.repository_descriptions_dir, tempdir)

	# Remote
	elif sys.argv[1] == 'remote':
		"""
		Download all files from the repository found in a given path, then perform analysis on it.
		Arguments:
			[2] - repository path to the file to download (including filename)
		"""
		if len(sys.argv) < 3:
			print("Usage: {} remote <project name>".format(sys.argv[0]))
			sys.exit(1)

		repository.set_project(sys.argv[2])
		repository.set_source(settings.repository_user_dir)
		repository.downloadFiles(settings.repository_descriptions_dir, tempdir)
		local_mode(tempdir, tempdir, False)

	# Local
	elif sys.argv[1] == 'local':
		"""
		Analyse a folder of XML files.
		Arguments:
			[2] - path to folder to analyse
			[3] - path to folder to write outputs to
		"""
		if len(sys.argv) < 4:
			print("Usage: {} local <input model dir> <output dir>".format(sys.argv[0]))
			sys.exit(1)
		inputdir = repository.enforce_trailing_slash(sys.argv[2])
		outputdir = repository.enforce_trailing_slash(sys.argv[3])
		local_mode(inputdir, outputdir, None, None, True)

	# Upload
	elif sys.argv[1] == 'upload':
		"""
		Upload a file to the Repository.
		Arguments:
			[2] - path to the file to upload
			[3] - project name in the repository
			[4] - repository source name
			[5] - path in the repository to upload to (including filename)
			[6] - what to set the "data_type" metadata to
			[7] - what to set the "checked" metadata to
		"""
		if len(sys.argv) < 6:
			print("Usage: {} upload <source file> <project name> <source name> <destpath> <data_type> <checked>"
				.format(sys.argv[0]))
			sys.exit(1)

		repository.set_project(sys.argv[3])
		repository.set_source(sys.argv[4])
		repository.uploadFile(sys.argv[2], sys.argv[5], sys.argv[6], sys.argv[7])
		print("Upload complete.")

	# Download
	elif sys.argv[1] == 'download':
		"""
		Download a file from the Repository.
		Arguments:
			[2] - project name in the repository
			[3] - repository source name
			[4] - path to the file to download (including filename)
			[5] - local path (including filename) to save the file as
		"""
		if len(sys.argv) < 4:
			print("Usage: {} download <project name> <source name> <file> <outputfile>".format(sys.argv[0]))
			sys.exit(1)

		repository.set_project(sys.argv[2])
		repository.set_source(sys.argv[3])
		repository.downloadFile(sys.argv[4], sys.argv[5])
		print("Download complete.")
			
	# Verify
	elif sys.argv[1] == 'verify':
		"""
		Check if we can see the other tools.
		"""
		rc = subprocess.call(['which', 'vivado_hls'], stdout=subprocess.PIPE)
		if rc == 0:
			print('Xilinx tools - OK')
		else:
			print(ANSI_RED + 'Missing Xilinx tools!' + ANSI_END)
			print('Please check if Vivado is installed and accessible.')
			sys.exit(1)

		repository.authenticate()
		print('Repository is assessible - OK')

		print("All Dependencies tests passed.")
		sys.exit(0)

	# List Deployments
	elif sys.argv[1] == 'listdeps':
		"""
		List all deployments in the given path.
		Arguments:
			[2] - project name in the repository to search for deployments
		"""
		if len(sys.argv) < 3:
			print("Usage: {} listdeps <deployments dir>".format(sys.argv[0]))
			sys.exit(1)
		
		repository.set_project(sys.argv[2])
		repository.set_source(settings.repository_user_dir)
		repository.listDeployments(settings.repository_descriptions_dir)

	else:
		print("Invalid mode.")
		print("Valid modes are: subscribe, remote, local, upload, download, verify, listdeps")
		sys.exit(1)



def local_mode(inputdir, outputdir, uploadoncedone, models = None, localmode = False):
	"""
	Read the model from inputdir, creating all output files into outputdir.
	If uploadoncedone, then the metadata in the repository is updated for each
	deployment tested according to the result.

	models should be a dictionary of the form:
	{ 'cn': 'filename.xml', 'pd': 'filename.xml', ['de': 'filename.xml'] }
	Otherwise the input directory will be searched for files that start with 'cn', 'pd', and 'de' respectively and will
	fail if they are not found, and apart from deployments, unique.
	
	If multiple deployments are found/specified they are all tested.

	inputdir and outputdir can be the same location.
	"""

	if models == None:
		models = find_input_models(inputdir)
		if len(models['de']) > 0:
			print(ANSI_CYAN + "Found {} deployments to process.\n".format(
				len(models['de']), "s" if len(models['de']) > 1 else "") + ANSI_END)

	#Prepare output directory
	try:
		os.makedirs(outputdir)
	except OSError as e:
		if e.errno != errno.EEXIST:
			raise

	#Now run an analysis for each deployment
	for dep in models['de']:
		print(ANSI_YELLOW + "Processing model: {} {} {}".format(os.path.basename(models['cn']),
			os.path.basename(models['pd']),	os.path.basename(models['de'][0])) + ANSI_END)
		#summarise_deployment(dep)
		generate_ipcores(dep, inputdir, outputdir, localmode)

	if len(models) == 0:
		print(ANSI_RED + "No valid deployments found." + ANSI_END)

	# Delete temporary files after finishing this run
	shutil.rmtree(tempdir)
	os.mkdir(tempdir)



def subscribe(repository_projectname, path, tempdir):
	"""
	Subscribe to a project using the Application Manager. Waits for updates to the project and
	analyses any checked deployments continually.
	"""
	def checkForUDs(path, tempdir):
		import time
		time.sleep(1) # We currently seem to have to give the metadata a little time to update inside the repository
		uds = repository.checkedDeployments(path)

		if(len(uds) > 0):
			print(ANSI_GREEN + "Project has {} checked deployment{}...\n".format(
				len(uds), "s" if len(uds) > 1 else "") + ANSI_END)

			# Download the files
			models = {} # This will tell local_mode which XML files are of which type

			cns = repository.downloadAllFilesOfType("componentnetwork", path, tempdir)
			if len(cns) != 1:
				print(ANSI_RED + "Multiple files of type 'componentnetwork' \
				found at path {} when only one was expected.".format(path) + ANSI_END)
				sys.exit(1)
			models['cn'] = os.path.join(tempdir, cns[0])

			pds = repository.downloadAllFilesOfType("platformdescription", path, tempdir)
			if len(pds) != 1:
				print(ANSI_RED + "Multiple files of type 'platformdescription' \
				found at path {} when only one was expected.".format(path) + ANSI_END)
				sys.exit(1)
			models['pd'] = os.path.join(tempdir, pds[0])
			
			deps = []
			for dep in uds:
				deps.extend([os.path.join(tempdir, dep['filename'])])
				repository.downloadFile(os.path.join(path, dep['filename']), 
					os.path.join(tempdir, dep['filename']), True, False)
			models['de'] = deps

			local_mode(tempdir, tempdir, path, models=models)

	print(ANSI_GREEN + "Subscribing to project {}. Waiting for updates...".format(path) + ANSI_END)
	
	try:
		ws = websocket.create_connection("ws://{}:{}".format(settings.app_manager_ip, settings.app_manager_port))
		req = "{{\"user\":\"{}\" , \"project\":\"{}\"}}".format(settings.repository_user, repository_projectname)
		ws.send(req)
		result = ws.recv()
	except ConnectionRefusedError:
		print(ANSI_RED + "Cannot connect to Application Manager." + ANSI_END)
		print("Response: {}".format(result)) if 'result' in locals() else None
		sys.exit(1)

	try:
		reply = json.loads(result)
		if not 'suscribed_to_project' in reply:
			raise json.decoder.JSONDecodeError
	except json.decoder.JSONDecodeError:
		print(ANSI_RED + "Invalid response from Application Manager. Response: {}".format(result))
		sys.exit(1)

	# Run a first check regardless of response from the websocket
	checkForUDs(path, tempdir)

	while True:
		try:
			result = ws.recv()
			reply = json.loads(result)

			if 'project' in reply and reply['project'] == repository_projectname:
				checkForUDs(path, tempdir)
		except json.decoder.JSONDecodeError:
			print(ANSI_RED + "Invalid response from Application Manager. Response: {}".format(result))
			sys.exit(1)



def find_input_models(inputdir):
	'''
	Determine input models as:
	{
		'cn': <inputdir>cn*.xml,
		'pd': <inputdir>pd*.xml,
		['de': <inputdir>de*.xml]
	}
	'''
	def deglob_input_models(pattern):
		'''
		Turn the provided pattern into an absolute filename. Also checks that the de-globbing is unique and
		outputs an error and exits if not.
		'''
		results = glob.glob(pattern)
		if(len(results) != 1):
			print("The pattern {} does not refer to a unique file.".format(pattern))
			sys.exit(1)
		else:
			return results[0]

	models = {
		'cn': deglob_input_models("{}cn*.xml".format(inputdir)),
		'pd': deglob_input_models("{}pd*.xml".format(inputdir))
	}

	models['de'] = glob.glob("{}de*.xml".format(inputdir))

	if len(models['de']) < 1:
		print("Cannot find deployments in directory {}".format(inputdir))
		sys.exit(1)
	return models



def summarise_deployment(filename):
	print(ANSI_MAGENTA + "Mappings:")
	doc = expatbuilder.parse(filename, False)
	mappings = doc.getElementsByTagName('mapping')
	for m in mappings:
		comp = m.getElementsByTagName('component')
		proc = m.getElementsByTagName('processor')
		if len(comp) == 1 and len(proc) == 1:
			print("\t{} -> {}".format(comp[0].getAttribute('name'), proc[0].getAttribute('name')))
	print(ANSI_END)



def generate_ipcores(filename, inputdir, outputdir, localmode):
	print(ANSI_MAGENTA + "\nMappings:")
	fpga_components = []
	doc = expatbuilder.parse(filename, False)
	mappings = doc.getElementsByTagName('mapping')

	for m in mappings:
		comp = m.getElementsByTagName('component')
		proc = m.getElementsByTagName('processor')

		if len(comp) == 1 and len(proc) == 1:
			print("\t{} -> {}".format(comp[0].getAttribute('name'), proc[0].getAttribute('name')))

		if proc[0].getAttribute('name') == 'fpga':
			fpga_components.append(comp[0].getAttribute('name'))
	
	print()
	for fpga_component in fpga_components:
		component_dir = "{}".format(fpga_component)
		tmpdir = os.path.join(tempdir, component_dir)
		
		if localmode == True:
			download_dir = os.path.join('../', srcfilesdir, component_dir)
			localdir = os.path.abspath(os.path.join(inputdir, download_dir))
			copy(localdir, tmpdir)
		else:
			download_dir = os.path.join(srcfilesdir, component_dir)
			repository.set_source(settings.repository_user_dir)
			repository.downloadFiles(download_dir, tmpdir)
			repository.set_source(repository_ipcoregen_source)
		
		top_function = "{}".format(fpga_component)
		src_file = "{}/{}.cpp".format(tmpdir, fpga_component)
		header_file = "{}/{}.h".format(tmpdir, fpga_component)

		timestamp = int(time.time())
		solution_name = "{}-{}".format(top_function, timestamp)
		
		# TODO call tools directly instead of using sh script
		exitcode = os.system("sh ipcore-generator.sh " + settings.target_fpga + " " + 
			solution_name + " "  + top_function + " " + src_file + " " + header_file)

		if exitcode == 0:
			print(ANSI_GREEN + "\nIP Core Generation Finished" + ANSI_END)

			ipcore_zip = "generated-ipcores/{}.zip".format(solution_name)

			if localmode == True:
				print(ANSI_CYAN + "\nSaving IP Core zip to output dir..." + ANSI_END)
				copy(ipcore_zip, outputdir)
			else:
				print(ANSI_CYAN + "\nUploading IP Core zip to Repository..." + ANSI_END)
				repository.uploadIPCoreZip(ipcore_zip, "generated-ipcores", "zip", top_function)

			# Delete Temporary Files
			print(ANSI_CYAN + "\nRemoving Temporary Files..." + ANSI_END)
			shutil.rmtree("generated-ipcores")
			shutil.rmtree("generated-src")
			
			print(ANSI_GREEN + "\nFinished")
		else:
			print(ANSI_RED + "\nIP Core Generation Failed - exitcode: {}".format(exitcode))

	repository.set_source(settings.repository_user_dir)
	print(ANSI_END)




def copy(src, dest):
    try:
        shutil.copytree(src, dest)
    except OSError as e:
        # If the error was caused because the source wasn't a directory
        if e.errno == errno.ENOTDIR:
            shutil.copy(src, dest)
        else:
            print('Directory not copied. Error: %s' % e)



if __name__ == "__main__":
	main()

