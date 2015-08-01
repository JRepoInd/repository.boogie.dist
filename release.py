# -*- coding: utf-8 -*-
import sys
import os
import shutil,stat
import urllib2
import urllib
import md5
import datetime
import time
import re
from distutils.version import StrictVersion, LooseVersion
from xml.dom import minidom

import shlex
from subprocess import Popen, PIPE

def runcmd(cmd,cwd):
	args = shlex.split(cmd)
	proc = Popen(args, stdout=PIPE, stderr=PIPE,cwd=cwd)
	out, err = proc.communicate()
	exitcode = proc.returncode
	#print out[:-1]
	return exitcode, out, err

dirname=os.path.dirname(os.path.realpath(__file__))
username="huseyinbiyik"
password=sys.argv[1]
distrepo={"repo":"repository.boogie.dist",
		  "branch":"master"}
packs={"plugin.program.ump":"master",
	   "repository.boogie":"master"}

datesince=int(time.mktime(datetime.datetime(2000,1,1).timetuple()))

def remove_readonly(func, path, excinfo):
	os.chmod(path, stat.S_IWRITE)
	func(path)

def download_zip(pack,branch):
	urllib2.urlopen("https://github.com/%s/%s/archive/%s.zip"%(uname,pack,branch))
	
def gitcli():
	c,o,e=runcmd("git fetch --all",dirname)
	c,o,e=runcmd("git reset --hard origin/master",dirname)
	c,o,e=runcmd("git pull https://%s:%s@github.com/%s/%s.git %s"%(username,password,username,distrepo["repo"],distrepo["branch"]),dirname)
	print "%s: Repo synched from upstream"%distrepo["repo"]
	for pack,branch in packs.iteritems():
		stage_path=os.path.join(dirname,"staging")
		repo_path= os.path.join(stage_path,pack)
		if os.path.exists(repo_path):
			shutil.rmtree(repo_path,onerror=remove_readonly)
		os.makedirs(repo_path)
		repo_url = 'https://github.com/%s/%s.git'%(username,pack)
		c,o,e=runcmd("git init",repo_path)
		c,o,e=runcmd("git remote add origin %s "%repo_url,repo_path)
		c,o,e=runcmd("git fetch",repo_path)
		c,o,e=runcmd("git tag -l",repo_path)
		c,o,e=runcmd("git show-ref --head",repo_path)
		last_version="0.0.0"
		last_hash=None
		head_hash=None
		for release in o.split("\n"):
			try:
				hash=release.split(" ")[0]
				if "tags/" in release.split(" ")[1]:
					version=release.split(" ")[1].split("/")[-1]
				elif "/"+branch in release.split(" ")[1]:
					head_hash=hash
					continue
				else:
					continue

				if LooseVersion(version)>LooseVersion(last_version):
					last_version=version
					last_hash=hash
			except:
				continue

		if not last_version=="0.0.0":
			c,o,e=runcmd("git log "+head_hash+" -n 1 --format=%at",repo_path)
			head_ts=int(o)
			c,o,e=runcmd("git log "+last_hash+" -n 1 --format=%at",repo_path)
			last_ts=int(o)
		if not last_version=="0.0.0" and head_ts>last_ts or last_version=="0.0.0":
			c,o,e=runcmd("git fetch --all",repo_path)
			c,o,e=runcmd("git pull https://%s:%s@github.com/%s/%s.git %s"%(username,password,username,pack,branch),repo_path)
			x=open(os.path.join(repo_path,"addon.xml")).read()
			new_version=LooseVersion(last_version).version
			new_version[2]=	str(int(new_version[2])+1)
			new_version=[str(x) for x in new_version]
			new_version = ".".join(new_version)
			print "%s: Found new version %s since %s"%(pack,new_version,last_version)
			c,log,e=runcmd('git log --pretty=format:"%ad: %s" --date short',repo_path)
			changelog=open(os.path.join(repo_path,"changelog.txt"),"w")
			changelog.truncate()
			changelog.write(log)
			changelog.close()
			addonxml = minidom.parse(os.path.join(repo_path,"addon.xml"))
			addon = addonxml.getElementsByTagName("addon")
			addon[0].attributes["version"].value=new_version
			addonxml.writexml( open(os.path.join(repo_path,"addon.xml"), 'w'),encoding="UTF-8")
			print "%s: New version bumped in addon.xml & changelog"%pack
			c,o,e=runcmd("git add -A .",repo_path)
			c,o,e=runcmd("git commit -m '%s Version Release'"%new_version,repo_path)
			c,o,e=runcmd("git tag -a %s -m '%s Version Release'"%(new_version,new_version),repo_path)
			c,o,e=runcmd("git push https://%s:%s@github.com/%s/%s.git %s"%(username,password,username,pack,branch),repo_path)
			c,o,e=runcmd("git push https://%s:%s@github.com/%s/%s.git %s --tags "%(username,password,username,pack,branch),repo_path)
			print "%s: Created new tag on github"%pack
			##download new packet and update binaries
			pack_path=os.path.join(dirname,pack)
			if os.path.exists(pack_path):
				shutil.rmtree(pack_path,onerror=remove_readonly)
			os.makedirs(pack_path)
			#urllib.urlretrieve("https://github.com/%s/%s/archive/%s.zip"%(username,pack,new_version),os.path.join(pack_path,"%s-%s.zip"%(pack,new_version)))
			shutil.rmtree(os.path.join(repo_path,".git"),onerror=remove_readonly)
			shutil.make_archive(os.path.join(pack_path,"%s-%s"%(pack,new_version)), 'zip', stage_path,pack)
			metas=["icon.png","fanart.jpg","changelog.txt"]
			for meta in metas:
				if os.path.exists(os.path.join(repo_path,meta)):
					shutil.copy2(os.path.join(repo_path,meta),os.path.join(pack_path,meta))
			print "%s: New zipball created on distribution directory"%pack
			##update addons.xml
			create_new=True
			addonsxml=minidom.parse(os.path.join(dirname,"addons.xml"))
			for addontag in addonsxml.getElementsByTagName("addons")[0].getElementsByTagName("addon"):
				if addontag.attributes["id"].value==pack:
					create_new=False
					addontag.attributes["version"].value=new_version
			if create_new:
				addonsxml.getElementsByTagName("addons")[0].appendChild(addon[0])
			addonsxml.writexml( open(os.path.join(dirname,"addons.xml"), 'w'),encoding="UTF-8")
			m = md5.new(open(os.path.join(dirname,"addons.xml")).read()).hexdigest()
			open(os.path.join(dirname,"addons.xml.md5"),"wb").write(m)
			print "%s: addons.xml and md5 is updated"%pack

			c,o,e=runcmd("git add -A .",dirname)
			c,o,e=runcmd("git commit -m '%s Version Release for %s'"%(new_version,pack),dirname)
			c,o,e=runcmd("git push https://%s:%s@github.com/%s/%s.git %s"%(username,password,username,distrepo["repo"],distrepo["branch"]),dirname)
			print "%s: Distribution repo updated"%pack
		else:
			print "%s: No new commits version:%s. Skipping"%(pack,last_version)
gitcli()