#!/bin/sh
# ------------------------------------------------------------------
# 
#	PHANTOM - IP Core Generator
# 
# ------------------------------------------------------------------

VERSION=0.1.0
SUBJECT=phantom-ip-core-generator
USAGE="Usage: ipcore-generator.sh <target_fpga> <solution_name> <top_function> <src_file> <header_file>"

ANSI_RED="\033[1;31m"
ANSI_GREEN="\033[1;32m"
ANSI_BLUE="\033[1;34m"
ANSI_CYAN="\033[1;36m"
ANSI_END="\033[0;0m"

# --- Options processing -------------------------------------------
if [ $# == 0 ] ; then
    echo $USAGE
    exit 1;
fi

if [ $# -lt 2 ] ; then
    echo "Script requires two arguments"
    echo "Argument 0: cpp file."
    echo "Argument 1: Top function name"
    exit 1;
fi

while getopts ":i:vh" optname
  do
    case "$optname" in
      "v")
        echo "Version $VERSION"
        exit 0;
        ;;
      "i")
        echo "-i argument: $OPTARG"
        ;;
      "h")
        echo $USAGE
        exit 0;
        ;;
      "?")
        echo "Unknown option $OPTARG"
        exit 0;
        ;;
      ":")
        echo "No argument value for option $OPTARG"
        exit 0;
        ;;
      *)
        echo "Unknown error while processing options"
        exit 0;
        ;;
    esac
  done

shift $(($OPTIND - 1))


# --- Locks -------------------------------------------------------
LOCK_FILE=/tmp/$SUBJECT.lock
if [ -f "$LOCK_FILE" ]; then
   echo "Script is already running"
   exit
fi

trap "rm -f $LOCK_FILE" EXIT
touch $LOCK_FILE

# --- Body --------------------------------------------------------

target_fpga=$1
solution_name=$2
top_function=$3
source_file=$4
if [ $# -ge 5 ]; then
    header_file=$5
fi

src_dir="$( cd "$( dirname "$2" )" && pwd )"


echo -e "$ANSI_CYAN"
echo -e "PHANTOM IP CORE GENERATOR $ANSI_END"
echo -e "$ANSI_BLUE	Solution: $ANSI_END \t $solution_name"
echo -e "$ANSI_BLUE	Top function: $ANSI_END \t $top_function"
#echo -e "$ANSI_BLUE	Src Dir: $ANSI_END \t $src_dir"
echo -e "$ANSI_BLUE	Source File: $ANSI_END \t $source_file"
if [ $# -ge 4 ]; then
    echo -e "$ANSI_BLUE	Header File: $ANSI_END \t $header_file"
fi


# Transform source code to be compatible with HLS interfaces
echo -e "$ANSI_CYAN"
echo -e "Transforming source code... $ANSI_END"
mkdir -p $src_dir/generated-src
./ipcore-rewriter $source_file > $src_dir/generated-src/$top_function-gen.cpp


# Call HLS to generate an IP Core
echo -e "$ANSI_CYAN"
echo -e "Generating IP Core... $ANSI_END"

if [ -e "$header_file" ]; then
    cp $header_file $src_dir/generated-src
    vivado_hls script.tcl -tclargs $target_fpga $solution_name $top_function $src_dir/generated-src/$top_function-gen.cpp $src_dir/generated-src/$top_function.h > /dev/null && {
    #vivado_hls script.tcl -tclargs $target_fpga $solution_name $top_function $src_dir/generated-src/$top_function-gen.cpp $src_dir/generated-src/$top_function.h && {

       echo -e "$ANSI_GREEN"
       echo "Success"
       echo -e "$ANSI_BLUE    Solution: $solution_name"
       echo -e "$ANSI_END"
    } || {
       echo 
       echo -e "$ANSI_RED Error! Operation aborted $ANSI_END"
       exit 1
    }

else
    vivado_hls script.tcl -tclargs $target_fpga $solution_name $top_function $src_dir/generated-src/$top_function-gen.cpp > /dev/null && {
    #vivado_hls script.tcl -tclargs $target_fpga $solution_name $top_function $src_dir/generated-src/$top_function-gen.cpp && {
       echo -e "$ANSI_GREEN"
       echo "Success"
       echo -e "$ANSI_BLUE    Solution: $solution_name"
       echo -e "$ANSI_END"
    } || {
       echo 
       echo -e "$ANSI_RED Error! Operation aborted $ANSI_END"
       exit 1
    }
fi

echo -e "$ANSI_CYAN""Compressing IP Core into zip archive... $ANSI_END"
cd generated-ipcores/ && zip -r $solution_name.zip $solution_name/ > ../zip.log && cd - > /dev/null

exit 0

# -----------------------------------------------------------------

