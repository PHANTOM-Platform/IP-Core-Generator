# IP-Core-Generator

## DEVELOPMENT GUIDE

### SYSTEM REQUIREMENTS
The IP Core Generator requires a PC running Linux. It was tested on Ubuntu 16.04 LTS and Ubuntu 18.04 LTS, with AMD64 architecture, but should also run on any other Linux distribution as long as the dependencies are met.

#### DEPENDENCIES
-  Xilinx Vivado tools with Zynq-7000 support (Tested with Vivado Design Suite 2016.4 and Vivado Design Suite 2017.4)
-  Git
-  Python3
-  Python3 module: websocket-client

#### DEPLOYMENT PROCEDURE
The IP Core Generator needs Xilinx Vivado tools, with Zynq-7000 support, to be installed and properly configured. Vivado Design Suite comes with all the necessary tools and can be downloaded from:
-  https://www.xilinx.com/support/download.html

Installation and Licensing information can be found here:
-  https://www.xilinx.com/support/documentation-navigation/design-hubs/dh0013-vivado-installation-and-licensing-hub.html

The Vivado Design Suite User Guide can be used as reference for detailed install instruction:
-  https://www.xilinx.com/support/documentation/sw_manuals/xilinx2017_3/ug973-vivado-release-notes-install-license.pdf

After installing Vivado Design Suite the tools must be imported into the current environment. It is necessary to source settings32.sh or settings64.sh (whichever is appropriate for the operating system) from the area in which the design tools are installed. This sets up the environment to point to this installed location. For example, for Vivado 2017.4, on the default install location:

`source /opt/Xilinx/Vivado/2017.4/settings64.sh`

Git and Python3 come pre-installed in most operating systems. If any of them is missing they can be installed with the following command:

`sudo apt install git python3 python3-pip`

Then the needed python modules can be installed using pip:

`python3 -m pip install websocket-client`

All the tool files can be downloaded to the current directory using git clone:
```
git clone https://github.com/PHANTOM-Platform/PHANTOM-IP-Core-Generator
git clone https://github.com/PHANTOM-Platform/IP-Core-Generator
```

Once everything has been installed, the tool can verify if the Xilinx tools are properly configured and accessible with:

`./ipcore-generator.sh verify`

### CONFIGURATION GUIDE
The IP Core Generator will need to know how to connect to the Repository and App Manager. For this the corresponding IP addresses and ports should be set in the file settings.py. Also, the user must input their credentials to allow the IP Core Generator to connect to the other PHANTOM modules.

```
# Set the Repository IP address and port
repository_ip = "localhost"
repository_port = 8000

# Set the Application Manager websocket IP address and port
app_manager_ip = "localhost"
app_manager_port = 8500

# Set the credentials for the Repository and Application Manager
repository_user = "username"
repository_pass = "password"
```

Besides, IP addresses, ports and credentials, the only extra parameter that should be configured is the model of the target FPGA device, so the IP Core generator can target the correct hardware.

```
# Set the target FPGA device - ZC706 = xc7z045ffg900-2
target_fpga = "xc7z045ffg900-2"
```

### USAGE GUIDE
The IP Core Generator works autonomously, reading newly added files when it receives a notification from the Application Manager. To receive notifications from the Application Manager it is necessary to subscribe to a project.

`./ipcore-generator.py subscribe project-name`

The tool will then automatically run when new deployments are checked by the Offline MOM. If there is any component mapped to a FPGA the IP Core Generator will fetch the respective source files from the Repository to proceed with the analysis and source code transformation. It then calls Xilinx tools to generate an IP core, compresses it into a zip file and uploads it to the Repository.

The tool will also create a modified version of the software component that includes all the necessary code to interface between FPGA hardware and software automatically. The modified component will also be uploaded to the Repository.

Finally, the IP Core Generator will modify the component network to include the new FPGA implementation and update it in the Repository.

#### MANUAL USAGE
If you do not want to subscribe using the Application Manager, you can trigger the IP Core Generator to manually on a project using the remote command:

`./ipcore-generator.py remote project-name`

Finally, to avoid all dependencies on the Application Manager and Repository, you can simply run on a local PHANTOM project folder with the local command:

`./ipcore-generator.py local /path/to/project/folder/`

The outputs of the IP Core Generator (IP Core zip and modified component source code) will be stored in the ipcore-generator directory inside the project folder.
