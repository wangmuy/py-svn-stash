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

import os
import shutil
import random
from subprocess import Popen, PIPE
from datetime import datetime

SVN_EXECUTABLE = 'svn'
HOME_DIR = os.path.expanduser("~")
CURRENT_DIR = os.getcwd()
SVN_STASH_DIR = os.path.join(HOME_DIR, ".svn-stash")
COMMAND_DEFAULT ="list"
TARGET_FILE_DEFAULT ="all"
STASH_REGISTER_FILENAME = ".stashed_register"

class svn_stash_register:
	"""A class to register all stashes."""
	def __init__(self):
		self.stashes = [] #list of stashes (with meta data) in the current dir
		self.all_stashes = [] #list of all stashes (with meta data) in all directories
		self.load() #load register

	def load(self):
		try:
			create_stash_dir_if_any()
			current_dir = os.path.join(SVN_STASH_DIR, STASH_REGISTER_FILENAME)
			with open(current_dir,"r") as f:
				for line in f:
					content = line.rstrip()
					content = content.split("\t")
					if len(content)>0:
						stash_meta = { 'id': content[0] }
						if ( len(content) > 1 ):
							stash_meta['comment'] = content[1]
						else:
							stash_meta['comment'] = ''
						if is_a_current_stash(stash_meta['id']):
							self.stashes.append(stash_meta)
						self.all_stashes.append(stash_meta)
				f.close()
		except IOError as e:
			print e
			print 'registerFile cannot be readed.'

	def write(self):
		try:
			create_stash_dir_if_any()
			current_dir = os.path.join(SVN_STASH_DIR, STASH_REGISTER_FILENAME)
			with open(current_dir,"w") as f:
				content = []
				for stash_meta in self.all_stashes:
					line = str(stash_meta['id']) + "\t" + str(stash_meta['comment']) + "\n"
					content.append(line)
				f.writelines(content)
				f.close()
		except IOError as e:
			print 'registerFile cannot be created.'

	def obtain_last_stash(self):
		length = len(self.stashes)
		if length>0:
			stash = svn_stash()
			stash_meta = self.stashes[length-1]
			stash.load(stash_meta['id'])
			return stash
		return False

	def obtain_stash_by_id(self,stash_id):
		for m in self.stashes:
			if ( m['id'] == stash_id ):
				stash = svn_stash()
				stash.load(m['id'])
				return stash
		return False

	def register_stash(self,stash): #stash must be a svn-stash instance
		stash_id = stash.key
		stash_comment = raw_input( "Comments make future-you happier: ")
		stash_meta = { 'id': stash_id, 'comment': stash_comment }
		self.stashes.append(stash_meta)
		self.all_stashes.append(stash_meta)
		stash.write()
		print "created stash " + str(stash_id)

	def delete_stash(self,stash):
		stash_id = stash.key
		self.stashes[:] = [d for d in self.stashes if d.get('id') != stash_id]
		self.all_stashes[:] = [d for d in self.all_stashes if d.get('id') != stash_id]
		self.write()
		#Remove stash files
		stash.clear()
		print "deleted stash " + str(stash_id)

	def list(self):
		for stash_meta in self.stashes:
			print stash_meta['id'] + "\t" + stash_meta['comment']

	def clear(self):
		self.list()
		confirm = raw_input( 'Really delete all this work? [Y/N]: ' )
		if ( not ( confirm == 'y') ):
			return
		ids = map(lambda x: x['id'], self.stashes)
		for id in ids:
			current_stash = svn_stash()
			current_stash.load(id)
			self.delete_stash(current_stash)

class svn_stash:
	"""A class to contain all information about stashes."""
	def __init__(self):
		self.files = {} #dictionary of files
		self.timestamp = datetime.now() #time of creation
		self.key = random.getrandbits(128) #unique identifier
		self.root_url = CURRENT_DIR

	def push(self,target_file,info):
		filename_list = info['files']
		flags = info['flags']
		filename_list = sorted(filename_list)
		filename_list.reverse()
		create_stash_dir_if_any()
		if target_file == "all":
			for filename in filename_list:
				self.push(filename,info)
		else:
			randkey = random.getrandbits(128) #unique identifier
			self.files[target_file] = randkey
			print "push " + target_file + "->" + str(randkey)
			if os.path.isfile(target_file) or os.path.isdir(target_file):
				with open(os.path.join(SVN_STASH_DIR, str(randkey) + '.stash.patch'), 'wb') as patch_file:
					result = execute_and_retrieve([SVN_EXECUTABLE, 'diff', '--internal-diff', target_file])
					patch_file.write(result[1])
				result = execute_and_retrieve([SVN_EXECUTABLE, 'revert', target_file])
				if flags[target_file] == 'A':
					if os.path.isfile(target_file):
						os.remove(target_file)
					if os.path.isdir(target_file):
						shutil.rmtree(target_file, ignore_errors=True)
				if flags[target_file] == 'D':
					if os.path.isdir(target_file):
						os.makedirs(target_file)
			# print "push end: " + target_file + "->" +  ", ".join(filename_list)

	def pop(self):
		result = ""
		if os.path.exists(SVN_STASH_DIR):
			file_list = self.file_list
			for target_file in file_list:
				randkey = self.files[target_file]
				filepath = os.path.join(SVN_STASH_DIR, str(randkey) + ".stash.patch")
				print 'pop: ' + target_file + "->" + filepath
				if os.path.isfile(filepath):
					if os.stat(filepath).st_size == 0 and not os.path.isdir(target_file):
						os.makedirs(target_file)
						result = execute_and_retrieve([SVN_EXECUTABLE, 'add', target_file])
						# print "added dir " + target_file
					elif not os.path.isfile(target_file):
						with open(target_file, 'a'):
							os.utime(target_file, None)  # Same as 'touch'
						result = execute_and_retrieve([SVN_EXECUTABLE, 'patch', filepath])
						result = execute_and_retrieve([SVN_EXECUTABLE, 'add', target_file])
						# print "added file " + target_file
					else:
						result = execute_and_retrieve([SVN_EXECUTABLE, 'patch', filepath])
						print "patched file " + target_file
						# print "pop " + target_file
				else:
					print 'Patch file cannot be found: ' + target_file + "->" + filepath

	def write(self):
		#Create file for svn stash
		try:
			current_dir = os.path.join(SVN_STASH_DIR, str(self.key))
			with open(current_dir,"w") as f:
				content = []
				#add the first line with root url
				line = self.root_url + "\n"
				content.append(line)
				for target_file in self.files:
					line = target_file + " " + str(self.files[target_file]) + "\n"
					content.append(line)
				f.writelines(content)
				f.close()
		except IOError as e:
			print 'randFile cannot be created.'

	def clear(self):
		result = ""
		noaction = True
		if os.path.exists(SVN_STASH_DIR):
			for target_file in self.files:
				randkey = self.files[target_file]
				filepath = os.path.join(SVN_STASH_DIR, str(randkey) + ".stash.patch")
				if os.path.isfile(filepath):
					if not noaction:
						os.unlink(filepath)
				else:
					print 'randFile cannot be found.'

			filepath = os.path.join(SVN_STASH_DIR, str(self.key))
			if os.path.isfile(filepath):
				if not noaction:
					result += os.unlink(filepath)
			else:
				print 'registerFile cannot be found.'

	def load(self,stash_id):
		try:
			current_dir = os.path.join(SVN_STASH_DIR, str(stash_id))
			with open(current_dir,"r") as f:
				is_first = True
				for line in f:
					content = line.rstrip()
					#if is the first line, then it is the root url
					if is_first:
						self.root_url = content
						is_first = False
					#it is stashed filename, otherwise
					else:
						content = content.split(" ")
						if len(content)>=2:
							self.files[content[0]] = content[1]
				self.key = stash_id
				f.close()
			self.file_list = self.files.keys()
			self.file_list = sorted(self.file_list)
		except IOError as e:
			print 'randFile cannot be read.'

	def __str__(self):
		content = print_hr(70)
		content += "stash " + str(self.key)
		content += print_hr(70)
		content += "root in: <" + self.root_url + ">\n"
		for filename in self.file_list:
			try:
				real_dir = self.files[filename] + ".stash.patch"
				current_dir = os.path.join(SVN_STASH_DIR, self.files[filename] + ".stash.patch")
				content += print_hr()
				content += "file " + real_dir
				content += print_hr()
				if os.stat(current_dir).st_size == 0:
					content += "Mkdir: " + filename + "\n"
				else:
					with open(current_dir,"r") as f:
						for line in f:
							content += line
						f.close()
			except IOError as e:
				content += 'randFile cannot be shown.\n'
		return content


########################
#Auxiliar functions    #
########################
#Create stash directory
def create_stash_dir_if_any():
	if not os.path.exists(SVN_STASH_DIR):
		os.makedirs(SVN_STASH_DIR)
	stash_register_file = os.path.join(SVN_STASH_DIR, STASH_REGISTER_FILENAME)
	if not os.path.exists(stash_register_file):
		try:
			f = open(stash_register_file, "w")
		except IOError:
			print "registerFile cannot be created."

def print_hr(lng=30):
	return "\n" + ("-"*lng) + "\n"

def is_a_current_stash(stash_id):
	stash = svn_stash()
	stash.load(stash_id)
	current_dir_parts = os.path.split(CURRENT_DIR)
	stash_dir_parts = os.path.split(stash.root_url)
	stash_dir_parts = stash_dir_parts[:len(current_dir_parts)]
	stash_dir = os.path.join(*stash_dir_parts)
	return stash_dir == CURRENT_DIR


def execute_and_retrieve(_cmd_args):
	cmd = find_executable(_cmd_args[0], os.environ['PATH'], implicitExt='.exe')
	process = Popen([cmd] + _cmd_args[1:], stdout=PIPE, stderr=PIPE)
	(stdout, stderr) = process.communicate()
	exit_code = process.wait()

	return exit_code, stdout, stderr

# Taken from: http://code.activestate.com/recipes/52224-find-a-file-given-a-search-path/#c4
def find_executable(seekName, path, implicitExt=''):
	"""Given a pathsep-delimited path string, find seekName.
	Returns path to seekName if found, otherwise None.
	Also allows for files with implicit extensions (eg, .exe), but
	always returning seekName as was provided.
	>>> findFile('ls', '/usr/bin:/bin', implicitExt='.exe')
	'/bin/ls'
	"""
	if os.path.isfile(seekName) or implicitExt and os.path.isfile(seekName + implicitExt):
		# Already absolute path.
		return seekName
	for p in path.split(os.pathsep):
		candidate = os.path.join(p, seekName)
		if os.path.isfile(candidate) or implicitExt and os.path.isfile(candidate + implicitExt):
			return candidate
	return None
