#!/usr/bin/env python3

import os, sys, glob, subprocess, json, time, shutil, errno, pathlib
import settings, repository
import websocket
from xml.dom import expatbuilder
from repository import ANSI_RED, ANSI_GREEN, ANSI_YELLOW, ANSI_BLUE, ANSI_MAGENTA, ANSI_CYAN, ANSI_END


# IP Core Generator Source Name
repository_ipcoregen_source = "ipcore-generator"

# Temporary Directories
tempdir = "_tmp/"
generated_ipcore_dir = "generated-ipcores"
generated_src_dir = "generated-src"

# Automatically clean temporary files
clean_temp = True;



def main():

	#Remove temporary directories
	if clean_temp:
		if os.path.isdir(generated_ipcore_dir):
			shutil.rmtree(generated_ipcore_dir)
		if os.path.isdir(generated_src_dir):
			shutil.rmtree(generated_src_dir)
		if os.path.isdir(tempdir):
			shutil.rmtree(tempdir)
	if not os.path.isdir(tempdir):
		os.mkdir(tempdir)


	# Usage
	if len(sys.argv) < 2:
		print("Usage: {} [mode] <args for mode>".format(sys.argv[0]))
		print("Valid modes are: subscribe, remote, local, source, upload, download, verify, listdeps, clean")
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
			print("Usage: {} subscribe <model-name>".format(sys.argv[0]))
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
			print("Usage: {} remote <project-name>".format(sys.argv[0]))
			sys.exit(1)

		repository.set_project(sys.argv[2])
		repository.set_source(settings.repository_pt_dir)
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
			print("Usage: {} local <input-model-dir> <output-dir>".format(sys.argv[0]))
			sys.exit(1)
		inputdir = repository.enforce_trailing_slash(sys.argv[2])
		outputdir = repository.enforce_trailing_slash(sys.argv[3])
		copytree(inputdir, tempdir)
		local_mode(tempdir, outputdir, True)

	# Source
	elif sys.argv[1] == 'source':
		"""
		Run the IP Core Generator on local source files
		Arguments:
			[2] - source filename
			[3] - header filename
			[4] - top function name
			[5] - output directory
		"""
		if len(sys.argv) < 6:
			print("Usage: {} source <source-file> <header-file> <top-funtion> <output-dir>"
				.format(sys.argv[0]))
			sys.exit(1)
		srcdir = repository.enforce_trailing_slash(os.path.relpath(os.path.dirname(sys.argv[2])))
		outputdir = repository.enforce_trailing_slash(os.path.relpath(sys.argv[5]))
		source_mode(srcdir, os.path.basename(sys.argv[2]), os.path.basename(sys.argv[3]), sys.argv[4], sys.argv[4], outputdir)

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
			print("Usage: {} upload <source-file> <project-name> <source-name> <destpath> <data-type> <checked>"
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
			print("Usage: {} download <project-name> <source-name> <file> <output-file>".format(sys.argv[0]))
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


		repository.set_project(sys.argv[2])
		repository.set_source(settings.repository_user_dir)
		repository.listDeployments(settings.repository_descriptions_dir)

	# Clean
	elif sys.argv[1] == 'clean':
		"""
		Deletes temporary files and folders
		"""
		if os.path.isdir(tempdir):
			shutil.rmtree(tempdir)
		if os.path.isdir(generated_ipcore_dir):
			shutil.rmtree(generated_ipcore_dir)
		if os.path.isdir(generated_src_dir):
			shutil.rmtree(generated_src_dir)
		if os.path.isdir('__pycache__'):
			shutil.rmtree('__pycache__')

	else:
		print("Invalid mode.")
		print("Valid modes are: subscribe, remote, local, source, upload, download, verify, listdeps, clean")
		sys.exit(1)

	# Delete temporary files on exit
	if clean_temp:
		if os.path.isdir(tempdir):
			shutil.rmtree(tempdir)



def subscribe(repository_projectname, path, tempdir):
	"""
	Subscribe to a project using the Application Manager. Waits for updates to the project and
	analyses any checked deployments continually.
	"""
	print(ANSI_GREEN + "Subscribing to project {}. Waiting for updates...".format(repository_projectname) + ANSI_END)

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

	repository.websocketUpdateStatus(repository_projectname, "ip_core_generator", "waiting")

	while True:
		try:
			result = ws.recv()
			reply = json.loads(result)

			if 'project' in reply and reply['project'] == repository_projectname:
				if 'pt_code_analysis' in reply and 'status' in reply['pt_code_analysis']:
					if reply['pt_code_analysis']['status'] == 'finished':
						print("PT Code Analysis finished - Starting IP Core Generator\n")
						repository.websocketUpdateStatus(repository_projectname, "ip_core_generator", "started")
						repository.set_project(sys.argv[2])
						repository.set_source(settings.repository_pt_dir)
						repository.downloadFiles(settings.repository_descriptions_dir, tempdir)
						local_mode(tempdir, tempdir, False)
						repository.websocketUpdateStatus(repository_projectname, "ip_core_generator", "finished")
						print("Exiting IP Core Generator")
						sys.exit(0)

		except json.decoder.JSONDecodeError:
			print(ANSI_RED + "Invalid response from Application Manager. Response: {}".format(result))
			sys.exit(1)



def local_mode(inputdir, outputdir, localmode = False):
	"""
	Read the Component Network from inputdir, creating all output files into outputdir.

	inputdir and outputdir can be the same location.
	"""

	if os.path.isfile(os.path.join(inputdir,settings.cn_name)): 
		# Prepare output directory
		os.makedirs(outputdir, exist_ok=True)

		# Run IP Core Generator
		print(ANSI_YELLOW + "\nProcessing Component Network: {} ".format(os.path.basename(settings.cn_name)) + ANSI_END)
		ipcore_generator(os.path.join(inputdir,settings.cn_name), inputdir, outputdir, localmode)

	else:
		print(ANSI_RED + "\nComponent Network not found." + ANSI_END)



def source_mode(srcdir, src_file, header_file, top_function, solution_name, outputdir):
	os.makedirs(generated_src_dir, exist_ok=True)
	copytree(srcdir, generated_src_dir)

	# Transform source code, generate IP Core and create modified software component
	exitcode = generateIPcore(generated_src_dir, src_file, header_file, top_function, solution_name)

	if exitcode == 0:
		# ZIP IP Core
		exitcode = os.system("cd " + generated_ipcore_dir + "/ && zip -r {}.zip {}/ > ../zip.log && cd - > /dev/null"
			.format(solution_name, solution_name))

	if exitcode == 0:
		print(ANSI_GREEN + "\nIP Core Generation Finished" + ANSI_END)

		ipcore_zip = os.path.join(generated_ipcore_dir, "{}.zip".format(solution_name))
		drivers_dir = os.path.join(generated_ipcore_dir, solution_name , "impl", "ip", "drivers",
			 top_function+"_top_v1_0", "src")

		# save Outputs
		print(ANSI_CYAN + "\nSaving files to output dir..." + ANSI_END)
		copy(ipcore_zip, os.path.join(outputdir, solution_name))
		copytree(generated_src_dir, os.path.join(outputdir, solution_name))
		copytree(drivers_dir, os.path.join(outputdir, solution_name, "drivers"))
		print(ANSI_GREEN + "\nFinished" + ANSI_END)
	else:
		print(ANSI_RED + "\nIP Core Generation Failed - exitcode: {}".format(exitcode) + ANSI_END)

	# Delete Temporary Files
	if clean_temp:
		if os.path.isdir(generated_ipcore_dir):
			shutil.rmtree(generated_ipcore_dir)
		if os.path.isdir(generated_src_dir):
			shutil.rmtree(generated_src_dir)
		if os.path.isdir(tempdir):
			shutil.rmtree(tempdir)



def ipcore_generator(componentNetwork, inputdir, outputdir, localmode):
	# Parse Deployment Plan and Component Network
	for fpga_component in getFPGAcomponentsFromCN(componentNetwork):
		CN_files = getfilesfromCN(componentNetwork, fpga_component, localmode, inputdir)
		
		for file in CN_files:
			top_function = "{}".format(file[1])
			tmpdir, src_file  = os.path.split(file[0])
			src_file = os.path.relpath(os.path.join(tmpdir, src_file), generated_src_dir)
			header_file = "{}.h".format(os.path.splitext(src_file)[0])
			
			#timestamp = int(time.time())
			#solution_name = "{}-{}".format(top_function, timestamp)
			solution_name = top_function

			os.makedirs(generated_src_dir, exist_ok=True)

			# Transform source code, generate IP Core and create modified software component
			exitcode = generateIPcore(generated_src_dir, src_file, header_file, top_function, solution_name)

			if exitcode == 0:
				# ZIP IP Core
				exitcode = os.system("cd " + generated_ipcore_dir + "/ && zip -r {}.zip {}/ > ../zip.log && cd - > /dev/null"
					.format(solution_name, solution_name))

			if exitcode == 0:
				print(ANSI_GREEN + "\nIP Core Generation Finished" + ANSI_END)

				ipcore_zip = os.path.join(generated_ipcore_dir, "{}.zip".format(solution_name))
				drivers_dir = os.path.join(generated_ipcore_dir, solution_name , "impl", "ip", "drivers",
					 top_function+"_top_v1_0", "src")

				# Add new implementation to Component Network
				files = [tmpdir, drivers_dir, ipcore_zip]
				addfilestoCN(componentNetwork, fpga_component, files, solution_name)

				# Upload to Repository or save locally
				if localmode == True:
					print(ANSI_CYAN + "\nSaving files to output dir..." + ANSI_END)
					copy(ipcore_zip,os.path.join(outputdir, solution_name))
					copytree(generated_src_dir, os.path.join(outputdir, solution_name))
					copytree(drivers_dir, os.path.join(outputdir, solution_name, os.path.relpath(tmpdir, generated_src_dir), "drivers"))
					copy(componentNetwork, outputdir)
				else:
					print(ANSI_CYAN + "\nUploading files to Repository..." + ANSI_END)
					repository.set_source(repository_ipcoregen_source)
					repository.uploadIPCoreZip(ipcore_zip, solution_name, "zip", top_function)
					repository.uploadDir(generated_src_dir, solution_name, "cpp")
					repository.uploadDir(drivers_dir, os.path.join(solution_name, os.path.relpath(tmpdir, generated_src_dir), "drivers"))
					#repository.set_source(settings.repository_user_dir)
					repository.uploadFile(componentNetwork, settings.repository_descriptions_dir, "componentnetwork")

				print(ANSI_GREEN + "\nFinished" + ANSI_END)
			else:
				print(ANSI_RED + "\nIP Core Generation Failed - exitcode: {}".format(exitcode) + ANSI_END)

	# Delete Temporary Files
	if clean_temp:
		if os.path.isdir(generated_ipcore_dir):
			shutil.rmtree(generated_ipcore_dir)
		if os.path.isdir(generated_src_dir):
			shutil.rmtree(generated_src_dir)
		if os.path.isdir(tempdir):
			shutil.rmtree(tempdir)
		os.mkdir(tempdir)



def generateIPcore(srcdir, srcfile, headerfile, top_function, solution_name):
	# IP Core Generator Start
	print(ANSI_CYAN + "\nPHANTOM IP CORE GENERATOR" + ANSI_END)
	print(ANSI_BLUE + "\tSolution: \t"     + ANSI_END + solution_name)
	print(ANSI_BLUE + "\tTop function: \t" + ANSI_END + top_function)
	print(ANSI_BLUE + "\tSource File: \t"  + ANSI_END + srcfile)
	print(ANSI_BLUE + "\tHeader File: \t"  + ANSI_END + headerfile)

	# Tranform source code
	print(ANSI_CYAN + "\nTransforming source code..." + ANSI_END)
	transformed_src = os.path.join(os.path.abspath(srcdir), srcfile)
	transformed_src_ip = os.path.join(os.path.abspath(srcdir), os.path.splitext(srcfile)[0] +"-ip"+ os.path.splitext(srcfile)[1])

	exitcode = os.system("./ipcore-rewriter " + os.path.join(srcdir, srcfile) + " " + transformed_src_ip)
	if not exitcode == 0:
		print(ANSI_RED + "Source code transformation failed!" + ANSI_END)
		return exitcode

	# Generate IP Core
	print(ANSI_CYAN + "\nGenerating IP Core..." + ANSI_END)
	exitcode = os.system("vivado_hls script.tcl -tclargs {} {} {} {} {}".format(settings.target_fpga, 
		solution_name, top_function, transformed_src_ip, os.path.join(srcdir, headerfile)))

	os.remove(transformed_src_ip)

	if not exitcode == 0:
		print(ANSI_RED + "IP Core Generation failed!" + ANSI_END)
		return exitcode
	else:
		print(ANSI_GREEN + "\nSuccess" + ANSI_END)
		print(ANSI_BLUE + "\tSolution: {}".format(solution_name) + ANSI_END)

	# Create modified software component
	print(ANSI_CYAN + "\nCreating modified software component with IP Core adapter..." + ANSI_END)
	exitcode = os.system("./ipcore-arm-adapter " + os.path.join(srcdir, srcfile) + " " + transformed_src)

	if not exitcode == 0:
		print(ANSI_RED + "Modified software component creation failed!" + ANSI_END)
	return exitcode



# Parse Deployment Plan	and get components mapped to FPGAs
def getFPGAcomponentsFromDP(deploymentPlan):
	print(ANSI_MAGENTA + "\nMappings:")
	fpga_components = []
	dp = expatbuilder.parse(deploymentPlan, False)
	mappings = dp.getElementsByTagName('mapping')

	for m in mappings:
		comp = m.getElementsByTagName('component')
		proc = m.getElementsByTagName('processor')

		if len(comp) == 1 and len(proc) == 1:
			print("\t{} -> {}".format(comp[0].getAttribute('name'), proc[0].getAttribute('name')))

		if proc[0].getAttribute('name') == "FPGA":
			fpga_components.append(comp[0].getAttribute('name'))
	print()
	return fpga_components



# Parse Component Network and get components with FPGA target
def getFPGAcomponentsFromCN(componentNetwork):
	print(ANSI_CYAN + "\nMappings:"+ANSI_END)
	fpga_components = []
	dp = expatbuilder.parse(componentNetwork, False)
	mappings = dp.getElementsByTagName('component')

	for m in mappings:
		devices = m.getElementsByTagName('devices')

		if len(devices) == 1:
			if  devices[0].getAttribute('FPGA').lower() == 'yes':
				print(ANSI_GREEN,end="")
				fpga_components.append(m.getAttribute('name'))
			else:
				print(ANSI_BLUE,end="")

			print("\t{:<15} ".format(m.getAttribute('name')),end="")
			print(ANSI_BLUE+"CPU -> {:<5} GPU -> {:<5} ".format(devices[0].getAttribute('CPU'),
				devices[0].getAttribute('GPU')),end="")

			if  devices[0].getAttribute('FPGA').lower() == 'yes':
				print(ANSI_GREEN,end="")
			else:
				print(ANSI_BLUE,end="")

			print("FPGA -> {:<5}".format(devices[0].getAttribute('FPGA')))

	print(ANSI_END)
	return fpga_components



# Parse Component Network and get files for the specified component
def getfilesfromCN(componentNetwork, fpga_component, localmode, inputdir):
	cn = expatbuilder.parse(componentNetwork, False)
	dirs = []

	for component in cn.getElementsByTagName('component'):
		if component.getAttribute('name') == fpga_component:
			for implementation in component.getElementsByTagName('implementation'):
				if implementation.getAttribute('id') == "1":
					for source_file in implementation.getElementsByTagName('source'):
						if source_file.getAttribute('path') not in dirs:
							dirs.append(source_file.getAttribute('path'))

	# Get Files
	for ddir in dirs:
		if localmode == True:
			localdir = os.path.abspath(os.path.join(inputdir, ddir))
			tmpdir = os.path.join(generated_src_dir, ddir)
			os.makedirs(tmpdir, exist_ok=True)
			copytree(localdir, tmpdir)
		else:
			repository.set_source(settings.repository_user_dir)
			tmpdir = os.path.join(generated_src_dir, ddir)
			os.makedirs(tmpdir, exist_ok=True)
			repository.downloadFiles(ddir, tmpdir)
			repository.set_source(repository_ipcoregen_source)

	files = []
	for ddir in dirs:
		for root, directories, filenames in os.walk(tmpdir):
			for filename in filenames:
				if os.path.isfile(os.path.join(tmpdir,filename)):
					with open(os.path.join(tmpdir,filename), 'r') as file:
						for line in file:
							if '#pragma ipcoregen function' in line:
								function_name = line.replace('#pragma ipcoregen function ', '').split()[0]
								relpath, filename = os.path.split(os.path.join(tmpdir,filename))
								file_funtion = [os.path.join(tmpdir,filename), function_name]
								files.append(file_funtion)
	return files



# Add new files to Component Network
def addfilestoCN(componentNetwork, fpga_component, files, solution_name):
	cn = expatbuilder.parse(componentNetwork, False)
	implementation_number = 0

	for component in cn.getElementsByTagName('component'):
		if component.getAttribute('name') == fpga_component:
			for implementation in component.getElementsByTagName('implementation'):
				if int(implementation.getAttribute('id')) > implementation_number:
					implementation_number = int(implementation.getAttribute('id'))

			newimpl = cn.createElement("implementation")
			newimpl.setAttribute("target", "fpga")
			newimpl.setAttribute("id", str(implementation_number+1))

			# Modified component files
			for root, directories, filenames in os.walk(files[0]):
				for filename in filenames:
					filepath = os.path.join(files[0], filename)
					filetype = "".join(pathlib.Path(filename).suffixes)[1:]
					if os.path.isfile(filepath):
						if filetype != "" and filetype != "h":
							relpath, filename = os.path.split(filepath)
							newsrc = cn.createElement("source")
							newsrc.setAttribute("file", filename)
							newsrc.setAttribute("lang", filetype)
							newsrc.setAttribute("path", os.path.join(repository_ipcoregen_source, solution_name,
								os.path.relpath(files[0], generated_src_dir)))
							newimpl.appendChild(newsrc)
					else:
						print("{} is not a valid file.".format(filepath))

			# Xilinx Autogenerated drivers
			for root, directories, filenames in os.walk(files[1]):
				for filename in filenames:
					filepath = os.path.join(files[1], filename)
					filetype = "".join(pathlib.Path(filename).suffixes)[1:]
					if os.path.isfile(filepath):
						if filetype != "" and filetype != "h":
							relpath, filename = os.path.split(filepath)
							newsrc = cn.createElement("source")
							newsrc.setAttribute("file", filename)
							newsrc.setAttribute("lang", filetype)
							newsrc.setAttribute("path", os.path.join(repository_ipcoregen_source, solution_name,
								os.path.relpath(files[0], generated_src_dir), 'drivers'))
							newimpl.appendChild(newsrc)
					else:
						print("{} is not a valid file.".format(filepath))

			# IP Core Zip
			relpath, filename = os.path.split(files[2])
			newsrc = cn.createElement("source")
			newsrc.setAttribute("file", filename)
			newsrc.setAttribute("lang", "ipcore")
			newsrc.setAttribute("path", os.path.join(repository_ipcoregen_source, solution_name))
			newimpl.appendChild(newsrc)

			# Write XML
			component.appendChild(newimpl)
			cnstring = cn.toprettyxml().replace("\r", "").replace("\n", "")
			cn = expatbuilder.parseString(cnstring, False)
			f = open(componentNetwork, "w+")
			cn.writexml(f, "", "\t", "\n")
			f.close()



def copy(src, dest):
	try:
		copytree(src, dest)
	except OSError as e:
		# If the error was caused because the source wasn't a directory
		if e.errno == errno.ENOTDIR:
			shutil.copy2(src, dest)
		else:
			print('Directory not copied. Error: %s' % e)



def copytree(src, dst, symlinks=False, ignore=None):
	if not os.path.exists(dst):
		os.makedirs(dst, exist_ok=True)
	if not os.path.isdir(src):
		shutil.copy2(src, dst)
	else:
		for item in os.listdir(src):
			s = os.path.join(src, item)
			d = os.path.join(dst, item)
			if os.path.isdir(s):
				copytree(s, d, symlinks, ignore)
			else:
				shutil.copy2(s, d)



if __name__ == "__main__":
	main()


