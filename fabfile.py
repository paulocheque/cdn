# coding: utf-8
from __future__ import with_statement
import codecs
import json
import os
import platform
import subprocess
import sys

from fabric.api import *
from fabric.colors import *
from fabric.utils import abort
from fabric.contrib.console import confirm

# Examples of Usage
# fab --list
# fab localhost bootstrap
# fab prepare
# fab rename:extension=jpg

# Environments

@task
def localhost():
    common()
    env.run = local
    env.sudo = local
    read_config_file('localhost.json')
    print(blue("Localhost"))

@task
def staging():
    common()
    if current_git_branch() != 'staging':
        if not confirm('Using staging environment without staging branch (%s). Are you sure?' % current_git_branch()):
            abort('cancelled by the user')
    env.venv = 'envstaging'
    env.python = 'python2.7'
    read_config_file('staging.json')
    print(blue("Staging"))

@task
def production():
    common()
    if current_git_branch() != 'master':
        if not confirm('Using production environment without master branch (%s). Are you sure?' % current_git_branch()):
            abort('cancelled by the user')
    read_config_file('production.json')
    print(blue("Production"))

def common():
    env.run = local
    env.sudo = local
    env.git_repository = ''
    env.app_path = '.'
    env.user = 'ubuntu'
    env.venv = 'env'
    env.python = 'pypy'
    env.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', '')
    env.aws_secret_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
    env.aws_region = os.getenv('AWS_REGION', '')
    env.aws_bucket = 'weblibraries'

def read_config_file(filename):
    """
    Example of the file localhost.json:
    {
        "ami": "123",
        "hosts": ["a.com", "b.com"]
    }
    """
    if os.path.exists(filename):
        with codecs.open(filename, 'r', 'utf-8') as f:
           data = json.loads(f.read())
           print(data)
           env.update(data)


# Utilities

def current_git_branch():
    label = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
    return label.strip()

def isMac():
    return platform.system().lower() == 'darwin'

def isLinux():
    return platform.system().lower() == 'linux'

def venv():
    return 'source %(env)s/bin/activate' % dict(env=env.venv)

def python(command):
  return 'python %(command)s' % dict(command=command)

def manage(command):
  return 'python manage.py %(command)s' % dict(command=command)

def install(packages):
    packages = ' '.join(packages)
    if isMac():
        env.run('brew install %(packages)s' % dict(packages=packages))
    elif isLinux():
        env.sudo('apt-get install -y %(package)s' % dict(package=packages))

def get_or_create_bucket(name, public=True, cors=None):
    with cd(env.app_path), prefix(venv()):
        import boto
        from boto.s3.cors import CORSConfiguration
        conn = boto.connect_s3() # read AWS env vars
        bucket = conn.lookup(name)
        if bucket is None:
            print('Creating bucket %s' % name)
            bucket = conn.create_bucket(name)
            if public:
                bucket.set_acl('public-read')
            if cors:
                cors_cfg = CORSConfiguration()
                cors_cfg.add_rule(['PUT', 'POST', 'DELETE'], cors, allowed_header='*', max_age_seconds=3000, expose_header='x-amz-server-side-encryption')
                cors_cfg.add_rule('GET', '*')
                bucket.set_cors(cors_cfg)
        return bucket

def upload_file_to_s3(bucket_name, filename, public=True, static_headers=False, gzip=False):
    bucket = get_or_create_bucket(bucket_name, cors='http://%s' % env.host_string)
    print('Uploading %s to Amazon S3 bucket %s' % (filename, bucket_name))
    k = bucket.new_key(filename)
    if static_headers:
        content_types = {
            '.js': 'application/x-javascript',
            '.map': 'application/json',
            '.json': 'application/json',
            '.css': 'text/css',
            '.html': 'text/html',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.png': 'image/png',
            '.pdf': 'application/pdf',
        }
        dir_filename, extension = os.path.splitext(filename)
        k.set_metadata('Content-Type', content_types.get(extension, 'text/plain'))
        k.set_metadata('Cache-Control', 'max-age=31536000')
        k.set_metadata('Expires', 'Thu, 31 Dec 2015 23:59:59 GM')
        if gzip:
            k.set_metadata('Content-Encoding', 'gzip')
    def percent_cb(complete, total):
        sys.stdout.write('.')
        sys.stdout.flush()
    k.set_contents_from_filename(filename, cb=percent_cb, num_cb=10)
    if public:
        k.set_acl('public-read')

def minify_js(jsfile):
    if jsfile.endswith('.js'):
        # env.run('sudo npm install uglify-js -g')
        dir_filename, extension = os.path.splitext(jsfile)
        fmin = dir_filename + '.min' + extension
        fmap = dir_filename + '.min' + extension + '.map'
        # FIXME: zuou app.js
        env.run('uglifyjs %s -o %s --source-map %s -p relative -c -m' % (jsfile, fmin, fmap))
        return fmin, fmap
    return jsfile, jsfile

def compress(textfile):
    env.run('gzip -9 %s' % textfile)
    env.run('mv %s.gz %s' % (textfile, textfile))
    return textfile

# Tasks

def upload_files_to_s3(files, public=True, static_headers=False, gzip=False):
    for f in files:
        upload_file_to_s3('weblibraries', f, public=True, static_headers=False, gzip=False)

@task
def bootstrap():
    print(red("Configuring application"))
    install('imagemagick')
    with cd(env.app_path):
        env.run('virtualenv %(env)s -p %(python)s' % dict(env=env.venv, python=env.python))
        with prefix(venv()):
            env.run('pip install -r requirements.txt')
    print(green("Bootstrap success"))

@task
def upload_common_static_files():
    print(red("Uploading common static files to S3"))
    files = ['static/common.js', 'static/common.css']
    for f in files:
        upload_file_to_s3('weblibraries', f, public=True, static_headers=True)
        if f.endswith('.js'):
            fmin, fmap = minify_js(f)
            upload_file_to_s3('weblibraries', fmin, public=True, static_headers=True)
            upload_file_to_s3('weblibraries', fmap, public=True, static_headers=True)


@task
def rename(folder='.', extension=None):
    output = '%(folder)s/output' % dict(folder=folder)
    local('rm -rf %(output)s && mkdir %(output)s' % dict(output=output))
    (_, _, filenames) = os.walk(folder).next()
    i = 1
    for filename in filenames:
        name, ext = os.path.splitext(filename)
        ext = ext.lower()
        if extension is None or extension in ext:
            newfilename = str(i).zfill(4)
            newfile = '%(output)s/%(newfilename)s%(ext)s' % dict(output=output, newfilename=newfilename, ext=ext)
            local('cp %(filename)s %(newfile)s' % dict(filename=filename, newfile=newfile))
            i += 1

@task
def convert(options, source, result):
    local('convert %(options)s %(source)s %(result)s' % dict(options=options, source=source, result=result))

@task
def convert_all(options, folder='.'):
    output = '%(folder)s/output' % dict(folder=folder)
    local('rm -rf %(output)s && mkdir %(output)s' % dict(output=output))
    (_, _, filenames) = os.walk(folder).next()
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    for filename in filenames:
        name, ext = os.path.splitext(filename)
        if ext.lower() in image_extensions:
            source = '%(folder)s/%(input)s' % dict(folder=folder, input=filename)
            result = '%(output)s/%(input)s' % dict(output=output, input=filename)
            convert(options, source, result)


@task
def upload_rest_client():
  files = [
    "libs/secret-rest-client/enc-base64.min.js",
    "libs/secret-rest-client/hmac-sha256.min.js",
    "libs/secret-rest-client/jquery.form.min.js",
    "libs/secret-rest-client/secret-rest-client.js",
  ]
  upload_files_to_s3(files)

@task
def upload_data_table():
  files = [
    "libs/secret-data-table/secret-data-table.js",
  ]
  upload_files_to_s3(files)

@task
def upload_bootstrap():
  # netdna.bootstrapcdn.com/bootstrap/3.1.0
  files = [
    "libs/bootstrap/bootstrap-theme.min.css",
    "libs/bootstrap/bootstrap.min.css",
    "libs/bootstrap/bootstrap.min.js",
    "libs/bootstrap/font-awesome.css",
  ]
  upload_files_to_s3(files)

@task
def upload_all(): # => [:upload_rest_client, :upload_data_table, :upload_bootstrap] do
  files = [
    "libs/ba-linkify.min.js",
    "libs/bootstrap-maxlength.min.js",
    "libs/jqBootstrapValidation.min.js",
    "libs/jquery-2.0.3.min.js",
    "libs/jquery.form.min.js",
    "libs/jquery.maskedinput.min.js",
    "libs/jquery.tablesorter.min.js",
    "libs/moment.min.js",
    "libs/pnotify/jquery.pnotify.default.css",
    "libs/pnotify/jquery.pnotify.default.icons.css",
    "libs/pnotify/jquery.pnotify.min.js",
    "libs/jquery-ui/jquery-ui-1.10.4.custom.min.js",
  ]
  upload_files_to_s3(files)

@task
def upload_file(file=None):
  # rake upload_file file=filepath
  filename = ENV["file"]
  upload_files_to_s3([filename])
