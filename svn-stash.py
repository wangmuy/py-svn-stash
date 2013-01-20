#    This file is part of svn-stash.

#    svn-stash is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    svn-stash is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with svn-stash.  If not, see <http://www.gnu.org/licenses/>.

import os,sys
import random
from datetime import datetime
from svn_stash_register import svn_stash_register,svn_stash,HOME_DIR,CURRENT_DIR,SVN_STASH_DIR,COMMAND_DEFAULT,TARGET_FILE_DEFAULT

def execute_stash_push(target_file,filename_list):
	stash = svn_stash()
	stash.push(target_file,filename_list)		
	register = svn_stash_register()
	register.register_stash(stash)
	register.write()

def execute_stash_pop(target_file,filename_list):
	#obtain last stash pop
	register = svn_stash_register()
	stash = register.obtain_last_stash()
	stash.pop()
	register.delete_stash(stash)

def execute_stash_list(target_file,filename_list):
	#obtain the list of stashes.
	register = svn_stash_register()
	for stash_id in register.stashes:
		print stash_id

def execute_stash_clear(target_file,filename_list):
	#delete all stashes.
	register = svn_stash_register()
	register.stashes = []
	register.write()

def execute_stash_show(target_file,filename_list):
	#view all diffs of all stashes.
	register = svn_stash_register()
	for stash_id in register.stashes:
		current_stash = svn_stash()
		current_stash.load(stash_id)
		print current_stash		

#Parser order and file of the command
def execute_svn_stash(command,target_file,filename_list):
	print command+","+target_file
	if command == "push":
		execute_stash_push(target_file,filename_list)
	elif command == "pop":
		execute_stash_pop(target_file,filename_list)
	elif command == "list":
		execute_stash_list(target_file,filename_list)
	elif command == "clear":
		execute_stash_clear(target_file,filename_list)
	elif command == "show":
		execute_stash_show(target_file,filename_list)

#obtain the svn status files
def obtain_svn_status_files():
	status_files = [] 
	status_list = os.popen('svn st').read()
	status_list = status_list.split("\n")
	for line in status_list:
		words = line.split()
		if len(words) > 1:
			(status,filename) = line.split()
			if status == "M":
				status_files.append(filename)
	print "status_files: ",status_files
	return status_files

def main(args):
	command = COMMAND_DEFAULT
	if len(args)>1:
		command = args[1]
	
	target_file = TARGET_FILE_DEFAULT
	if len(args)>2:
		target_file = args[2]
	
	filename_list = obtain_svn_status_files()
	execute_svn_stash(command,target_file,filename_list)


if __name__ == '__main__':
    main(sys.argv)