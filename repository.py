import requests, os, sys, json, io, pathlib
import settings

ANSI_RED = "\033[1;31m"; ANSI_GREEN = "\033[1;32m";  ANSI_BLUE = "\033[1;34m"; ANSI_END = "\033[0;0m";
ANSI_MAGENTA = "\033[1;35m"; ANSI_YELLOW = "\033[1;33m"; ANSI_CYAN = "\033[1;36m"; 

repository_projectname = None
repository_source = None


def authenticate():
	"""
	Authenticate with the repository
	Returns the OAuth token, or exits if authentication fails.
	"""
	repo_token_url = "http://{}:{}/login?email={}&pw={}".format(
		settings.repository_ip, settings.repository_port, settings.repository_user, settings.repository_pass)

	try:
		headers = {'content-type': 'text/plain'}
		rv = requests.get(repo_token_url, headers=headers)
		if rv.status_code != 200:
			print("Could not log in to repository. Status code: {}\n{}".format(rv.status_code, rv.text))
			sys.exit(1)
		return rv.text
	except requests.exceptions.ConnectionError as e:
		print(ANSI_RED + "Connection refused when connecting to the repository. " + ANSI_END)
		print(str(e))
		sys.exit(1)



def set_project(projectname):
	global repository_projectname
	repository_projectname = projectname

def get_project():
	global repository_projectname
	return repository_projectname


def set_source(source):
	global repository_source
	repository_source = source

def get_source():
	global repository_source
	return repository_source



def websocketUpdate(headers, project):
	"""
	Ping an update to the Application Manager for the project
	"""
	uploadjson = "{{\"project\": \"{}\", \"source\": \"{}\"}}".format(project, repository_source)

	url = "http://{}:{}/update_project_tasks".format(settings.app_manager_ip, settings.app_manager_port)

	rv = requests.post(url, files={'UploadJSON': uploadjson}, headers=headers)

	if rv.status_code != 200 and rv.status_code != 420:
		print("Could not update task. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)
		
		
		
def websocketUpdateStatus(status, project):
	"""
	Ping an update to the Application Manager for the project
	"""
	token = authenticate()
	
	headers = {'Authorization': "OAuth {}".format(token)}
	
	uploadjson = "{{\"project\": \"{}\", \"ip_core_generator\":{{\"status\":\"{}\"}} }}".format(project, status)
	
	url = "http://{}:{}/update_project_tasks".format(settings.app_manager_ip, settings.app_manager_port)

	rv = requests.post(url, files={'UploadJSON': uploadjson}, headers=headers)

	if rv.status_code != 200 and rv.status_code != 420:
		print("Could not update task. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)
	
	websocketFlush(project)	



def websocketFlush(project):
	"""
	Flush the Application Manager updates for the project
	"""
	token = authenticate()
	
	headers = {'Authorization': "OAuth {}".format(token)}
	
	url = "http://{}:{}/_flush".format(settings.app_manager_ip, settings.app_manager_port)

	rv = requests.get(url, files={}, headers=headers)

	if rv.status_code != 200 and rv.status_code != 420:
		print("Could not update task. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)



# Download Files

def getAllFilesOfType(type, path):
	"""
	Returns a list of metadata of the specified data type at the given path
	"""
	token = authenticate()

	url = "http://{}:{}/query_metadata?project={}&source={}&Path={}".format(
		settings.repository_ip, settings.repository_port, repository_projectname, repository_source, path)

	headers = {'Authorization': "OAuth {}".format(token), 'Content-Type': 'multipart/form-data'}

	rv = requests.get(url, headers=headers)

	if rv.status_code != 200:
		print("Could not download file from the repository. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)
	try:
		reply = json.loads(rv.text)

	except json.decoder.JSONDecodeError:
		print(ANSI_RED + "Invalid response from Application Manager. Response: {}".format(rv.text))
		sys.exit(1)
	
	rv = []
	for hit in reply:
		if hit['data_type'] == type:
			rv.append(hit)
	return rv



def downloadAllFilesOfType(type, path, outputdir):
	"""
	Download all files that match a certain type and save them in the outputdir
	"""
	rv = []
	fls = getAllFilesOfType(type, path)
	for f in fls:
		downloadFile(enforce_trailing_slash(path) + f['filename'], enforce_trailing_slash(outputdir) + f['filename'], True, False)
		rv.append(f['filename'])
	return rv



def downloadFile(filetodownload, destfile, save=True, verbose=True):
	"""
	Download the requested file from the repository and save it locally
	"""
	token = authenticate()

	url = "http://{}:{}/download?project={}&source={}&filepath={}&filename={}".format(
		settings.repository_ip, settings.repository_port, repository_projectname, repository_source,
		os.path.dirname(filetodownload), os.path.basename(filetodownload))

	headers = {'Authorization': "OAuth {}".format(token), 'Content-Type': 'multipart/form-data'}

	rv = requests.get(url, headers=headers)

	if rv.status_code != 200:
		print("Could not download file from the repository. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)

	if save:
		with open(destfile, 'w+') as file:
			file.write(rv.text)
		if verbose: print("\t{}".format(filetodownload))
	else:
		return rv.text



def downloadFiles(srcdir, targetdir):
	"""
	Download the entire contents of a given directory in the repository to targetdir
	Hidden files (that begin with a .) are not downloaded.
	"""
	token = authenticate()

	url = "http://{}:{}/downloadlist?project={}&source={}&filepath={}".format(
		settings.repository_ip, settings.repository_port, repository_projectname, repository_source, srcdir)

	headers = {'Authorization': "OAuth {}".format(token), 'Content-Type': 'multipart/form-data'}

	rv = requests.get(url, headers=headers)

	if not os.path.isdir(targetdir):
		os.mkdir(targetdir)

	print(ANSI_CYAN + "Fetching files from repository..." + ANSI_END)

	for fn in rv.text.split('\n'):
		if len(fn) > 0 and os.path.basename(fn)[0] != '.':
			downloadFile(srcdir + "/" + os.path.basename(fn), targetdir + "/" + os.path.basename(fn))



# Upload Files

def upload(filetoupload, filename, destpath, data_type, checked, websocket_update):
	"""
	Upload the given file object to the repository. If websocket_update then the
	metadata for the given file is updated, which will notify all subscribers
	"""
	token = authenticate()

	url = "http://{}:{}/upload?project={}&source={}&DestFileName={}&Path={}".format(
		settings.repository_ip, settings.repository_port, repository_projectname, repository_source, filename, destpath)
	
	headers = {'Authorization': "OAuth {}".format(token)}
	
	if checked is None:
		uploadjson = "{{\"project\": \"{}\", \"source\": \"{}\", \"data_type\": \"{}\"}}"\
			.format(repository_projectname, repository_source, data_type)
	else:
		uploadjson = "{{\"project\": \"{}\", \"source\": \"{}\", \"data_type\": \"{}\", \"checked\": \"{}\"}}"\
			.format(repository_projectname, repository_source, data_type, checked)
		
	files = {
		'UploadFile': filetoupload,
		'UploadJSON': uploadjson
	}

	rv = requests.post(url, files=files, headers=headers)

	if rv.status_code != 200:
		print("Could not upload file to repository. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)

	if websocket_update:
		websocketUpdate(headers, repository_projectname)



def uploadFile(filetoupload, destpath, data_type, checked=None, websocket_update=True):
	"""
	Upload the given file to the repository. "filetoupload" must be a path to a valid file.
	"""
	if not os.path.isfile(filetoupload):
		print("{} is not a valid file.".format(filetoupload))
		sys.exit(1)
	filename = os.path.basename(filetoupload)
	return upload(open(filetoupload, 'rb'), filename, destpath, data_type, checked, websocket_update)



def uploadDir(dirtoupload, destpath, checked=None, websocket_update=True):
	"""
	Upload the given directory, files and subfolders to the repository. "dirtoupload" must be a path to a valid directory.
	"""
	def files(path): 
		for root, directories, filenames in os.walk(path):
			for filename in filenames:
				yield os.path.relpath(os.path.join(root, filename), path)
	
	for file in files(dirtoupload):
		filepath = os.path.join(dirtoupload, file)
		if os.path.isfile(filepath): 
			relpath, filename = os.path.split(file)
			upload(open(filepath, 'rb'), filename, os.path.join(destpath, relpath), 
				"".join(pathlib.Path(file).suffixes), checked, websocket_update)
		else:
			print("{} is not a valid file.".format(filepath))



def uploadFileContents(filecontents, filename, destpath, data_type, checked, websocket_update=True):
	"""
	Upload the given file contents to the repository as filename at the given path.
	"""
	stringAsFile = io.StringIO(filecontents)
	return upload(stringAsFile, filename, destpath, data_type, checked, websocket_update)



def uploadIPCoreZip(filetoupload, destpath, data_type, ipcore_name, websocket_update=True):
	"""
	Upload the given file to the repository. If websocket_update then the
	metadata for the given file is updated, which will notify all subscribers
	"""
	token = authenticate()

	if not os.path.isfile(filetoupload):
		print("{} is not a valid file.".format(filetoupload))
		sys.exit(1)

	url = "http://{}:{}/upload?project={}&source={}&DestFileName={}&Path={}".format(
		settings.repository_ip,	settings.repository_port, repository_projectname, repository_source,
		os.path.basename(filetoupload),	destpath)

	headers = {'Authorization': "OAuth {}".format(token)}

	uploadjson = "{{\"project\": \"{}\", \"source\": \"{}\", \"data_type\": \"{}\", \"ipcore_name\": \"{}\"}}".format(
		repository_projectname, repository_source, data_type, ipcore_name)

	files = {
		'UploadFile': open(filetoupload, 'rb'),
		'UploadJSON': uploadjson
	}

	rv = requests.post(url, files=files, headers=headers)

	if rv.status_code != 200  and rv.status_code != 420:
		print("Could not upload file to repository. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)

	if websocket_update:
		websocketUpdate(headers, repository_projectname)



# Metadata

def getMetadata(path, filename):
	"""
	Get the metadata for a specified file.
	Returns a JSON as follows:
	{
		[
			{metadata for file}
			...
		]
	}
	This will usually only be one hit.
	"""
	token = authenticate()

	url = "http://{}:{}/query_metadata?project={}&source={}&Path={}&filename={}".format(
		settings.repository_ip, settings.repository_port, repository_projectname, repository_source, path, filename)

	headers = {'Authorization': "OAuth {}".format(token), 'Content-Type': 'multipart/form-data'}

	rv = requests.get(url, headers=headers)

	if rv.status_code != 200:
		print("Could not download metadata from the repository. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)
	try:
		reply = json.loads(rv.text)
	except json.decoder.JSONDecodeError:
		print(ANSI_RED + "Invalid response from Application Manager. Response: {}".format(rv.text))
		sys.exit(1)
	return reply



def setMetadata(filename, path, uploadjson, websocket_update=True):
	"""
	Edit the metadata of a file. Unfortunately we have to download and reupload the file to change its
	metadata.
	"""
	filedata = downloadFile(enforce_trailing_slash(path) + filename, None, False)

	token = authenticate()

	url = "http://{}:{}/upload?project={}&source={}&DestFileName={}&Path={}".format(
		settings.repository_ip, settings.repository_port, repository_projectname, repository_source, filename, path)

	headers = {'Authorization': "OAuth {}".format(token)}
	files = {'UploadFile': io.StringIO(filedata), 'UploadJSON': uploadjson}

	rv = requests.post(url, files=files, headers=headers)
	if rv.status_code != 200:
		print("Could not upload file to repository. Status code: {}\n{}".format(rv.status_code, rv.text))
		sys.exit(1)

	if websocket_update:
		websocketUpdate(headers, repository_projectname)



# Deployments

def uncheckedDeployments(path):
	"""
	Returns the unchecked deployments for the given path
	"""
	rv = getAllFilesOfType("deployment", path)
	r = []
	for hit in rv:
		if not 'checked' in hit or hit['checked'] == "no":
			r.append(hit)
	return r



def checkedDeployments(path):
	"""
	Returns the checked deployments for the given path
	"""
	rv = getAllFilesOfType("deployment", path)
	r = []
	for hit in rv:
		if hit['checked'] == "yes":
			r.append(hit)
	return r



def listDeployments(path):
	"""
	Pretty print the deployments
	"""
	rv = getAllFilesOfType("deployment", path)
	r = []
	print("All deployments:")
	for hit in rv:
		if not 'checked' in hit or hit['checked'] == "no":
			print("\t" + hit['filename'] + ": unchecked")
		else:
			if(hit['checked'] == 'yes'):
				print("\t" + hit['filename'] + ": Passed all checks")
			else:
				print("\t" + hit['filename'] + ": Failed on test '" + hit['checked'] + "'")



# Utils

def enforce_trailing_slash(path):
	'''
	Returns path, with the '/' character appended if it did not already end with it
	'''
	if path[-1] != '/':
		return path + '/'
	else:
		return path


